## Design

We have two implementations of the proxy server

#### HTTP proxy server

The HTTP proxy design uses a Python based Flask web server

The request to get a key from Redis is implemented with a HTTP GET on the /get endpoint.
The key is passed via the query param. So, to get a key via cURL, you may do:

```curl localhost:6000/get?key=name```

If a key is not found, the API returns status code 404.

##### LRU cache internals

The LRU (Least Recently Used) cache is implemented with a doubly linked list (DLL) and a hashmap <key to DLL node>. 
When an item is access/ upserted, the node is moved to the head of the DLL.
The hashmap is required to lookup the node corresponding to a key in O(1).
When the DLL reaches capacity, the tail of the DLL is removed.
Thus, the get/ set / delete operations on the LRU occur in O(1) time.

##### LRU cache expiration

A background thread called the 'LRU janitor' is spawned when the server starts 
for the first time. This thread periodically removes any keys that may have expired.
To track the expiry, we store the time in the DLL node of the LRU cache 
when a key is upserted.

#### RESP proxy server

I reimplemented the core GET, SET and DEL methods via the Redis's RESP protocol
I created a simple TCP server that listens on the RESP_PORT port.

It then processes the binary input in O(n) time and O(1) space by using a single index
to keep track of the current position in the array.
For this approach, it was helpful to develop this in a functional programming appraoch and avoiding any state. 
This made it easy to add support for 'pipelining' multiple commands by simple 
running a while loop till the end of the array was reached.
The RESP implementation does not support LRU, expiry, concurrency, etc. 
If I had more time, it is easy to add support for it.

## Concurrency

The critical section in a GET request occurs whenever the LRU is accessed.
The LRU is not thread safe due to its usage of a doubly linked list (DLL).
Without that the correct ordering of elements in the DLL will not be maintained.
In the worst case, there may be dangling pointers in the DLL which could lead to
 memory leaks and huge proportion of cache misses.
Hence, a lock must be acquired before the LRU is accessed. 

I initially used a single global lock for both the cache hit and cache miss scenarios.
But, since they will never occur together for the same requesting thread, 
I used separate locks to reduce starvation: one for cache hit and one for cache miss. 
Note that for cache miss, we also need to lock access to redis with the same lock.

To allow multiple concurrent requests, I used a semaphore with a configured 
count beyond which it would block. However, in reality, the actual concurrent 
requests will be determined by how fast a thread can access the LRU. So, 
I would spent more effort making the LRU thread safe. 

## Tests
To run the tests. There is a unit test for the LRU functionality. 
There is an end to end API test for the testing the web service and 
the RESP service.

```make test```


## To start the proxy server

We have two implementations of the proxy server

##### Starting the HTTP proxy server

To start the HTTP based proxy server

```make restart``` 

or if you want to see the logs and run it in foreground 

```make restart_fg```

The default configuration is specified in the config/env.local file. 
Additionally, it is possible to override these parameters.
For example, To run the web server/ tests on a different port

```FLASK_RUN_PORT=7000 make restart``` 

or

```FLASK_RUN_PORT=8000 make test```

##### Starting the RESP proxy server
Similarly, to run the RESP proxy server
```RESP_PORT=21000 make restart_resp``` 

or to run the test with the RESP server on a different port
```RESP_PORT=21000 make test```

## Requirements Implemented and Time Spent

HTTP service + Single backing Redis instance: 1 hours

Global expiry: 1 hours

Cached get + LRU eviction + Fixed key size: 1.5 hours

Sequential + Concurrent concurrent processing + : 1.5 hour, having difficulty implementing 
a reliable unit tests

Configuration: 1 hours

Tests: 1.5 hours

RESP protocol: 2 hours, added support for 'pipelining' multiple commands in a single call.

## Software Requirements

docker-compose >= 1.25.5 (This is primarily for the --env-file option 
which is not present on older docker-compose binaries)

python3 (for the unit tests)
