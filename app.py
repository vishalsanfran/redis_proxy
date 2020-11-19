from flask import Flask, request
import logging
import os
import redis
import time
import threading
from lru import LRU

app = Flask(__name__)

pool = redis.ConnectionPool(
    host='{}'.format(os.environ.get('REDIS_HOST')),
    port=int(os.environ.get('REDIS_PORT')),
    max_connections=int(os.environ.get('MAX_CONN'))
)
lru = LRU(int(os.environ.get('CAPACITY')), int(os.environ.get('EXPIRY')))
log = logging.getLogger("redis-proxy")

get_lock = threading.RLock()
set_lock = threading.RLock()
semaphore = threading.Semaphore(int(os.environ.get('MAX_REQ')))

REDIS_CONN_RETRIES = 5
OFFSET = 10

@app.before_first_request
def janitor():
    thread = threading.Thread(target=lru.clean)
    thread.start()

@app.route('/')
def index():
    return 'Redis proxy service. Config:\n{}\n'.format(os.environ)

@app.route('/get')
def get():
    with semaphore:
        cnt = REDIS_CONN_RETRIES
        while True:
            try:
                return _get(request)
            except redis.exceptions.ConnectionError as ex:
                if cnt == 0:
                    raise ex
                cnt -= 1
                time.sleep(1.0)

def _get(request):
    key = request.args.get('key')
    if key is None:
        return app.make_response(("{} not found".format(key), 404))

    val = None
    try:
        with get_lock:
            val = lru.get(key)
        code = 200
    except KeyError:
        log.warn("{} not found in LRU".format(key))
    if val is None:
        with set_lock:
            val = redis.Redis(connection_pool=pool).get(key)
            if val is not None:
                log.warn("{} set in LRU".format(key))
                lru.set(key, val)
        code = 404 if val is None else 201
    msg = "{} not found".format(key) if code == 404 else val
    return app.make_response((msg, code))

@app.route('/set')
def set():
    key = request.args.get('key', None)
    val = request.args.get('val', None)
    redis.Redis(connection_pool=pool).set(key, val)
    return "{}:{}".format(key, val)

@app.route('/del')
def delete():
    key = request.args.get('key', None)
    try:
        lru.delete(key)
    except KeyError:
        log.warn("{} not found in LRU. Nothing to delete".format(key))
    redis.Redis(connection_pool=pool).delete(key)
    return "{}".format(key)
