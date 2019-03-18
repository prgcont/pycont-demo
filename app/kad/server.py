import os
import time
import math

from flask import Flask, render_template, make_response, request
from redis import Redis
from redis.exceptions import ConnectionError
from prometheus_client import generate_latest, CollectorRegistry, multiprocess, CONTENT_TYPE_LATEST

from .middleware import setup_metrics

redis_server = os.environ.get('REDIS_SERVER', 'localhost')
config_file = os.environ.get('CONFIG_FILE', '/etc/kad/config.yml')
redis = Redis(host=redis_server, port=6379)
notready_file = '/tmp/notready'


app = Flask(__name__)
setup_metrics(app)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route('/')
def index():
    hits = None
    redis_error = ""

    try:
        redis.incr('hits')
    except ConnectionError as err:
        redis_error = err
    else:
        hits = redis.get('hits').decode('utf8')

    envs = os.environ

    template_params = {
        'hits': hits,
        'envs': envs,
        'redis_server': redis_server,
        'config_file': config_file,
        'config_file_content': "",
        'redis_error': redis_error,
    }

    return render_template('index.html', **template_params)


@app.route('/slow')
def slow():
    time.sleep(3)
    return 'Slow request with sleep 3 seconds'


@app.route('/heavy')
def heavy():
    for x in range(999):
        if math.sqrt(math.pow(x, 100)) < 0:
            print("Never")

    return 'Heavy request executed'


@app.route('/check/live')
def live_check():
    return 'OK'


@app.route('/check/ready')
def ready_check():
    if os.path.isfile(notready_file):
        return "File {} exists, instance isn't ready".format(notready_file), 500
    else:
        return "OK"


@app.route('/action/terminate')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


@app.route('/metrics')
def metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)

    data = generate_latest(registry)

    response = make_response(data)
    response.headers['Content-Type'] = CONTENT_TYPE_LATEST
    response.headers['Content-Length'] = str(len(data))

    return response


def run():
    app.run(host="0.0.0.0", debug=True)
