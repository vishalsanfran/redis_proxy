import logging
import os
import redis
import socketserver

log = logging.getLogger("redis-proxy")

def to_bytes(val):
    return bytes(f"{val}\r\n", "utf-8")

def to_param_bytes(val):
    size = len(val) if isinstance(val, str) else len(str(val))
    return to_bytes(f'${size}') + to_bytes(val)

RESP_NULL = to_bytes('$-1')
RESP_OK = to_bytes('+OK')

def get_resp_err(msg):
    return to_bytes(f"-ERR {msg}")

def run_cmd(cmds):
    valid_cmds = set(['GET', 'SET', 'DEL'])
    if len(cmds) == 0 or cmds[0].upper() not in valid_cmds:
        raise ValueError("Invalid CMD {cmds}")
    if cmds[0] == 'GET':
        if len(cmds) != 2:
            raise ValueError("Invalid GET {cmds}")
        res = redis.Redis(connection_pool=pool).get(cmds[1])
        log.warning(f"doing GET on {cmds[1]} res {res}")
        ret = RESP_NULL if res is None else to_param_bytes(res.decode('utf-8'))
    elif cmds[0] == 'SET':
        if len(cmds) != 3:
            raise ValueError("Invalid SET {cmds}")
        log.warning(f"doing SET on key {cmds[1]} , val {cmds[2]}")
        redis.Redis(connection_pool=pool).set(cmds[1], cmds[2])
        ret = RESP_OK
    else:
        if len(cmds) != 2:
            raise ValueError("Invalid DEL {cmds}")
        redis.Redis(connection_pool=pool).delete(cmds[1])
        ret = RESP_OK
    return ret

def get_full_cmd(array, i):
    instr_cnt, i = parse_header(array, i)
    cmds, i = parse_instr_line(array, i, instr_cnt)
    ret = run_cmd(cmds)
    return ret, i

def parse_instr_line(array, i, cnt):
    res = []
    max_cnt, i = parse_num_line(array, i)
    cmd, i = get_cmd(array, i, max_cnt)
    res.append(cmd)
    for _ in range(cnt-1):
        max_cnt, i = parse_num_line(array, i)
        log.warning(f"var cnt {max_cnt} at i {i}")
        var, i = get_var(array, i, max_cnt)
        res.append(var)
    return res, i

def parse_header(array, i=0):
    return parse_count_line(array, '*', i)

def parse_num_line(array, i):
    return parse_count_line(array, '$', i)

def parse_count_line(array, beg, i):
    if array[i] != ord(beg):
        raise ValueError(f"Incorrect start of message {array[i]} expected {beg} at index {i}")
    try:
        cnt, i = get_cnt(array, i+1)
    except TypeError as e:
        #logging.warning(array)
        raise e
    return cnt, tail_check(array, i)

def tail_check(array, i):
    if i >= len(array):
        raise ValueError(f"Missing tail byte \r")
    if array[i] != ord('\r'):
        raise ValueError(f"Incorrect tail byte {array[i]} expected \r")
    i += 1
    if i >= len(array):
        raise ValueError(f"Missing tail byte \n")
    if array[i] != ord('\n'):
        raise ValueError(f"Incorrect tail byte {array[i]} expected \n")
    i += 1
    return i

def is_valid(byte, lo, hi):
    return byte >= lo and byte <= hi

def is_num(byte):
    return is_valid(byte, 48, 57)

def is_al(byte):
    return is_valid(byte, 65, 90) or is_valid(byte, 97, 122)

def is_punct(byte):
    return byte == 32 or byte == 44

def is_alnum(byte):
    return is_al(byte) or is_num(byte) or is_punct(byte)

def get_cnt(array, i):
    cnt = 0
    while i < len(array):
        if not is_num(array[i]):
            break
        cnt = cnt*10 + int(chr(array[i]))
        i += 1
    if cnt == 0:
        raise ValueError(f"Byte count cannot be zero")
    return cnt, i

def get_cmd(array, i, max_cnt):
    return get_alnum_func(array, i, max_cnt, is_al)

def get_var(array, i, max_cnt):
    return get_alnum_func(array, i, max_cnt, is_alnum)

def get_alnum_func(array, i, max_cnt, func):
    cnt = 0
    orig = i
    tot = orig + max_cnt
    while i < tot:
        if not func(array[i]):
            break
        i += 1
        cnt += 1
    if cnt < max_cnt:
        raise ValueError(f"Invalid bytes cnt_actual {cnt} expected {max_cnt} "
                         f"{array[orig:orig+cnt]} at {orig} {is_alnum(array[i])}")
    res = array[orig:orig+cnt].decode('utf-8')
    logging.warning(f"alnum is {res}")
    i = tail_check(array, i)
    return res, i

class RedisRespServer(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024)
        log.warning(f"{self.client_address[0]} sent {data} len {len(data)}")
        i = 0
        res = []
        try:
            while i < len(data):
                ret, i = get_full_cmd(data, i)
                res.append(ret)
        except ValueError as e:
            ret = get_resp_err(str(e))
            res.append(ret)
        ret_bytes = b''.join(res)
        logging.warning(f"returned {ret_bytes}")
        self.request.sendall(ret_bytes)


if __name__ == "__main__":
    pool = redis.ConnectionPool(
        host='{}'.format(os.environ.get('REDIS_HOST')),
        port=int(os.environ.get('REDIS_PORT')),
        max_connections=int(os.environ.get('MAX_CONN'))
    )
    port = int(os.environ['RESP_PORT'])
    with socketserver.TCPServer(('0.0.0.0', port), RedisRespServer) as server:
        log.warning(f"Redis RESP proxy server listening on port {port}")
        server.serve_forever()