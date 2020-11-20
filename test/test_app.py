import json
import requests
import unittest
import os
from dotenv import load_dotenv
import time
from lru import SLEEP_TIME
load_dotenv('config/env.test')
FIX1 = 'fixtures/person1.json'
BASE_URL = "http://localhost:{}".format(os.environ['FLASK_RUN_PORT'])


def load_fixture(path):
    with open(path) as f:
        d = json.load(f)
    for k,v in d.items():
        r = requests.get('{}/set'.format(BASE_URL), params={'key': k, 'val': v})
        assert r.status_code == 200
    return d

def unload_fixture(path):
    with open(path) as f:
        d = json.load(f)
    for k,_ in d.items():
        r = requests.get('{}/del'.format(BASE_URL), params={'key': k})
        assert r.status_code == 200
    return d

class TestApp(unittest.TestCase):
    def test_get_fixture1_loaded_expiry(self):
        unload_fixture(FIX1)
        d = load_fixture(FIX1)
        self.helper_cache_miss(d) #cache miss
        self.helper_cache_hit(d) #cache hit
        time.sleep(int(os.environ['EXPIRY']) + SLEEP_TIME + 1)
        self.helper_cache_miss(d) #keys have expired

    def test_get_fixture1_unloaded(self):
        d = unload_fixture(FIX1)
        for k, _ in d.items():
            r = requests.get('{}/get'.format(BASE_URL), params={'key': k})
            self.assertEqual(r.status_code, 404)

    def test_get_missing(self):
        keys = [None, "missing_key"]
        for k in keys:
            r = requests.get('{}/get'.format(BASE_URL), params={'key': k})
            self.assertEqual(r.status_code, 404)
            self.assertEqual(str(r.text), "{} not found".format(k))

    def helper_found(self, d, code):
        for k, v in d.items():
            r = requests.get('{}/get'.format(BASE_URL), params={'key': k})
            self.assertEqual(r.status_code, code)

    def helper_cache_hit(self, d):
        return self.helper_found(d, 200)

    def helper_cache_miss(self, d):
        return self.helper_found(d, 201)

    @classmethod
    def tearDownClass(cls):
        unload_fixture(FIX1)
