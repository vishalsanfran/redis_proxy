import time

DEFAULT_EXPIRY = 99999
SLEEP_TIME = 1.0

class Node(object):
    def __init__(self, key, val):
        self.next = None
        self.prev = None
        self.key = key
        self.val = val
        self.time = time.time()

class LRU(object):
    def __init__(self, cap, expiry=DEFAULT_EXPIRY):
        self.head = Node(-1,-1)
        self.tail = Node(-1,-1)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.cap = cap
        self.cnt = 0
        self.nd = {}
        self.expiry = expiry

    def remove_node(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def add_node_to_head(self, node):
        tmp = self.head.next
        node.prev = self.head
        self.head.next = node
        node.next = tmp
        tmp.prev = node

    def refresh(self, node):
        self.remove_node(node)
        self.add_node_to_head(node)

    def get(self, key):
        if key not in self.nd:
            raise KeyError
        self.refresh(self.nd[key])
        return self.nd[key].val

    def set(self, key, val):
        if key in self.nd:
            self.refresh(self.nd[key])
            self.nd[key].val = val
            self.nd[key].time = time.time()
        else:
            self.cnt += 1
            node = Node(key, val)
            self.nd[key] = node
            self.add_node_to_head(node)
            if self.cnt == self.cap+1:
                self.cnt -= 1
                node = self.tail.prev
                self.remove_node(node)
                self.nd.pop(node.key)

    def delete(self, key):
        if key not in self.nd:
            raise KeyError
        self.remove_node(self.nd[key])
        self.cnt -= 1
        self.nd.pop(key)

    def clean(self):
        while 1 == 1:
            for node in list(self.nd.values()):
                if time.time() > self.expiry + node.time:
                    self.delete(node.key)
            time.sleep(SLEEP_TIME)
