import unittest

from lru import LRU

class TestApp(unittest.TestCase):
    def test_update_item(self):
        lru = LRU(5)
        lru.set("name", "john")
        self.assertEqual(lru.cnt, 1)
        lru.set("age", 30)
        self.assertEqual(lru.get("name"), "john")
        lru.set("yob", 1990)
        self.assertEqual(lru.cnt, 3)
        lru.set("name", "jim")
        self.assertEqual(lru.get("name"), "jim")
        self.assertEqual(lru.cnt, 3)

    def test_set_above_cap(self):
        lru = LRU(3)
        lru.set("name", "john")
        self.assertEqual(lru.cnt, 1)
        lru.set("age", 30)
        lru.set("yob", 1990)
        self.assertEqual(lru.get("name"), "john")
        self.assertEqual(lru.get("age"), 30)
        self.assertEqual(lru.cnt, 3)
        self.assertEqual(lru.tail.prev.key, "yob")
        lru.set("loc", "CA")
        self.assertEqual(lru.cnt, 3)
        self.assertEqual(lru.tail.prev.key, "name")
        with self.assertRaises(KeyError):
            lru.get("yob")