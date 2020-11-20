import json
import os
import socket
import unittest
from dotenv import load_dotenv
load_dotenv('config/env.test')

from resp import RESP_NULL, RESP_OK, to_bytes, to_param_bytes, get_cnt

port = int(os.environ['RESP_PORT'])
FIX1 = 'fixtures/person1.json'

def get(key):
    return bytes(f"*2\r\n$3\r\nGET\r\n", "utf-8") + to_param_bytes(key)

def delete(key):
    return bytes(f"*2\r\n$3\r\nDEL\r\n", "utf-8") + to_param_bytes(key)

def set(key, val):
    return bytes(f"*3\r\n$3\r\nSET\r\n", "utf-8") + to_param_bytes(key) + to_param_bytes(val)

def unload_fixture(path):
    with open(path) as f:
        d = json.load(f)
    for k,_ in d.items():
        assert get_resp(delete(k)) == RESP_OK
    return d

def load_fixture(path):
    with open(path) as f:
        d = json.load(f)
    for k, v in d.items():
        assert get_resp(set(k, v)) == RESP_OK
    return d

def get_resp(req):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(('localhost', port))
        sock.sendall(req)
        received = sock.recv(1024)
    return received



class TestResp(unittest.TestCase):
    def test_del_get_missing_pipelined(self):
        self.assertEqual(get_resp(delete('name')+get('name')+set('name', 'John')+get('name')),
            RESP_OK + RESP_NULL + RESP_OK + to_param_bytes('John'))

    def test_fixture_del_get_set(self):
        unload_fixture(FIX1)
        d = load_fixture(FIX1)
        self.helper_found(d)

    def test_get_cnt(self):
        cnt, i = get_cnt(b'$15\r\n', 1)
        self.assertEqual(i, 3)
        self.assertEqual(cnt, 15)

    def helper_found(self, d):
        for k, v in d.items():
            self.assertEqual(get_resp(get(k)), to_param_bytes(v))
