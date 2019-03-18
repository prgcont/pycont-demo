#!/usr/bin/env python

from kubernetes import client, config
from datetime import datetime, timedelta
import time
import requests
import os
from requests.auth import HTTPBasicAuth

LATENCY_TRESHOLD_MS = 10
MY_NAMESPACE = os.environ.get("CURRENT_NAMESPACE", "pycont")
PROM_USER = os.environ.get("PROMETHEUS_USERNAME", "")
PROM_PASSWORD = os.environ.get("PROMETHEUS_PASSWORD", "")
CURRENT_NAME = os.environ.get("CURRENT_NAME", "pycont-operator")

# cache for keeping track of last runs
last_runs = {}

try:
    config.load_incluster_config()
except:
    config.load_kube_config()

apps_v1_beta = client.AppsV1beta1Api()


def list_namespace_deployments(namespace):
    deployments = apps_v1_beta.list_namespaced_deployment(namespace=namespace)
    return deployments.items


def create_deployment_skeleton(namespace, name, replicas):
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec()
    # Create the specification of deployment
    spec = client.AppsV1beta1DeploymentSpec(replicas=replicas, template=template)

    # Instantiate the deployment object
    deployment = client.AppsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec,
    )

    return deployment


# Increments replicas and patches deployment
def scale_deployment(namespace, name, replicas):
    r = replicas + 1
    d = create_deployment_skeleton(namespace, name, r)
    d.metadata.labels = {"last_scaling": datetime.now().isoformat().replace(":", "_")}
    print("Scaling deployment %s in namespace %s to %d replicas" % (name, namespace, r))
    apps_v1_beta.patch_namespaced_deployment_scale(
        name=name, namespace=namespace, body=d
    )


def should_scale(namespace, name, latency_treshold):
    if in_cooldown(namespace, name) or check_latency(namespace, name, latency_treshold):
        return True

    return False


def check_latency(namespace, name, latency_treshold):
    # TODO check latency for this app
    prom_url = "http://pyvo.prgcont.cz/prometheus/api/v1/query"
    query_data = {
        "query": 'http_requests_total{job="kubernetes-node-kubelet", handler="prometheus"}[5m]'
    }
    r = requests.post(
        prom_url, data=query_data, auth=HTTPBasicAuth(PROM_USER, PROM_PASSWORD)
    )
    if r.ok:
        print(r.json())
    else:
        print("Failed to query Prometheus, status code: {}".format(r.status_code))
    return False


def in_cooldown(namespace, name):
    key = "{}/{}".format(namespace, name)
    now = datetime.utcnow()
    cooldown_limit = now - timedelta(seconds=60)
    last = last_runs.get(key)

    if (last is None) or (last < cooldown_limit):
        print("Cooldown: Deployment {} should be updated".format(key))
        last_runs[key] = now
        return True

    print("Cooldown: Deployment {} is in cooldown, should not be scaled".format(key))
    return False


def main():
    namespace = MY_NAMESPACE
    latency_treshold = LATENCY_TRESHOLD_MS

    while True:
        deployments = list_namespace_deployments(namespace)
        print("Finding deployments in namespace %s" % namespace)
        for d in deployments:
            name = d.metadata.name
            replicas = d.spec.replicas
            if name == CURRENT_NAME:
                print("Ignoring my deployment: {}".format(CURRENT_NAME))
                continue

            print("Checking deployment: %s" % name)
            if should_scale(namespace, name, latency_treshold):
                scale_deployment(namespace, name, replicas)

        print("Sleeping for 5 seconds")
        time.sleep(5)


if __name__ == "__main__":
    # main()
    check_latency("", "", 60)
