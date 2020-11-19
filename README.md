Design
--------
This design uses a Python based Flask web server

```
Client --> [LRU Cache] -> [Flask web server]  <- HTTP/GET -> [Redis]
               ^
               |
           [LRU Janitor]
```

The request to get a key from Redis is implemented with a HTTP GET on the /get endpoint.
The key is passed via the query param. So, to get a key via cURL, you may do:

```curl localhost:6000/get?key=name```

If a key is not found, the API returns status code 404.
The LRU cache is implemented with a doubly linked list (DLL) and a hashmap <key to DLL node>. 
When an item is access/ upserted, the node is moved to the head of the DLL.
The hashmap is required to lookup the node corresponding to a key in O(1).
When the DLL reaches capacity, the tail of the DLL is removed.
Thus, the get/ set / delete operations on the LRU occur in O(1) time.

A background thread called the 'LRU janitor' is spawned when the server starts 
for the first time. This thread periodically removes any keys that may have expired.
To track the expiry, we store the time in the DLL node of the LRU cache 
when a key is upserted.

Tests
-----
To run the tests. There is a unit test for the LRU functionality. 
There is an end to end API test for the testing the web service.

```make test```

--------------------------
To start the proxy server
------------------------

```make restart``` 

or if you want to see the logs and run it in foreground 

```make restart_fg```

The default configuration is specified in the config/env.local file. 
Additionally, it is possible to override these parameters.
For example, To run the web server/ tests on a different port

```FLASK_RUN_PORT=7000 make restart``` 

or

```FLASK_RUN_PORT=8000 make test```

Requirements Implemented and Time Spent
------------
HTTP service + Single backing Redis instance: 1 hours

Global expiry: 1 hours

Cached get + LRU eviction + Fixed key size: 1.5 hours

Sequential + Concurrent concurrent processing + : 1.5 hour, having difficulty implementing 
a reliable unit tests

Configuration: 1 hours

Tests: 1.5 hours

Needed
-------
docker-compose >= 1.25 


