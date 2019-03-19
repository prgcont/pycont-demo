#!/usr/bin/env python

from kubernetes import client, config
from datetime import datetime, timedelta
import time
import requests
import os
from requests.auth import HTTPBasicAuth

LATENCY_SLO = 0.8
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
    if replicas <= 0:
        print("scale_deployment: invalid number of replicas {}".format(replicas))
        return False

    d = create_deployment_skeleton(namespace, name, replicas)
    d.metadata.labels = {"last_scaling": datetime.now().isoformat().replace(":", "_")}
    print("scale_deployment: scaling deployment %s in namespace %s to %d replicas" % (name, namespace, replicas))
    apps_v1_beta.patch_namespaced_deployment_scale(
        name=name, namespace=namespace, body=d
    )


'''
should scale determines if and how the deployment should scale.
returns 0 if nothing should be done
return 1 if scale up
returns -1 if scale down
'''
def should_scale(namespace, name, latency_treshold):
    if in_cooldown(namespace, name):
        return 0

    if high_latency(namespace, name, latency_treshold):
        return 1

    if low_latency(namespace, name, 0.95):
        return -1

    return 0


def low_latency(namespace, name, latency_treshold):
    val = latency_rate_5m(namespace, name)
    if not val:
        print("low_latency: Failed to receive latency}")
        return False

    if val >= latency_treshold:
        print("low_latency: current value {} is larger than treshold {}".format(val, latency_treshold))
        return True

    print("low_latency: current value {} is smaller than treshold {}".format(val, latency_treshold))
    return False


def high_latency(namespace, name, latency_treshold):
    val = latency_rate_5m(namespace, name)
    if not val:
        print("high_latency: Failed to receive latency}")
        return False

    if val <= latency_treshold:
        print("high_latency: current value {} is smaller than treshold {}".format(val, latency_treshold))
        return True

    print("high_latency: current value {} is larger or equal than treshold {}".format(val, latency_treshold))
    return False


'''
latency_rate_5m queries prometheus for percentage (0 to 1) of queries
faster than 0.5s in past 5 minutes.
returns 0 in case of error
'''
def latency_rate_5m(namespace, name):
    prom_url = "http://pyvo.prgcont.cz/prometheus/api/v1/query"
    query_data = {
        "query": 'sum(rate(request_latency_bucket{le="0.5"}[5m])) by (job) / sum(rate(request_latency_count[5m])) by (job)'
    }
    r = requests.post(
        prom_url, data=query_data, auth=HTTPBasicAuth(PROM_USER, PROM_PASSWORD)
    )
    if not r.ok:
        print("latency_rate_5m: Failed to query Prometheus, status code: {}".format(r.status_code))
        return 0

    o = r.json()
    results = o.get("data").get("result")
    if o.get("status") != "success" or len(results) < 1:
        print("latency_rate_5m: Incompatible result {} of query {}".format(o, query_data))
        return 0

    val = int(results[0].get("value")[1])
    return val


def in_cooldown(namespace, name):
    key = "{}/{}".format(namespace, name)
    now = datetime.utcnow()
    cooldown_limit = now - timedelta(seconds=60)
    last = last_runs.get(key)

    if (last is None) or (last < cooldown_limit):
        print("Cooldown: Deployment {} can be updated".format(key))
        last_runs[key] = now
        return False

    print("Cooldown: Deployment {} is in cooldown, should not be scaled".format(key))
    return True


def main():
    namespace = MY_NAMESPACE
    latency_treshold = LATENCY_SLO

    while True:
        deployments = list_namespace_deployments(namespace)
        print("Finding deployments in namespace %s" % namespace)
        for d in deployments:
            name = d.metadata.name
            if name != 'kad':
                print("Ignoring my deployment: {}".format(name))
                continue

            replicas = d.spec.replicas

            print("Checking deployment: %s" % name)
            s = should_scale(namespace, name, latency_treshold)
            if s:
                scale_deployment(namespace, name, replicas + s)

        print("Sleeping for 5 seconds")
        time.sleep(5)


if __name__ == "__main__":
    main()
