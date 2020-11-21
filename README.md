## Problem Statement

The task is to create a proxy service for the Redis datastore.
The list of requirements are as follows:
1. HTTP web service: Clients interface to the Redis proxy through HTTP, with the
 Redis “GET” command mapped to the HTTP “GET” method. Note that the proxy still 
 uses the Redis protocol to communicate with the backend Redis server.
2. Single backing instance: Each instance of the proxy service is associated 
with a single Redis service instance (called the “backing Redis”). The address 
of the backing Redis is configured at proxy startup.
3. Cached GET: A GET request, directed at the proxy, returns the value of the 
specified key from the proxy’s local cache if the local cache contains a value 
for that key. If the local cache does not contain a value for the specified key,
 it fetches the value from the backing Redis instance, using the Redis GET command,
  and stores it in the local cache, associated with the specified key.
4. Global expiry: Entries added to the proxy cache are expired after being in the
 cache for a time duration that is globally configured (per instance). After an 
 entry is expired, a GET request will act as if the value associated with the key
  was never stored in the cache.
5. LRU eviction: Once the cache fills to capacity, the least recently used (i.e.
 read) key is evicted each time a new key needs to be added to the cache.
6. Fixed key size: The cache capacity is configured in terms of number of keys it retains.
7. Sequential concurrent processing: Multiple clients are able to concurrently 
connect to the proxy (up to some configurable maximum limit) without adversely 
impacting the functional behaviour of the proxy. When multiple clients make concurrent
 requests to the proxy, it is acceptable for them to be processed sequentially 
 (i.e. a request from the second only starts processing after the first request has
  completed and a response has been returned to the first client).
8. Configuration: The following parameters are configurable at the proxy startup:
                  Address of the backing Redis
                  Cache expiry time
                  Capacity (number of keys)
                  TCP/IP port number the proxy listens on
9. System tests: Automated systems tests confirm that the end-to-end system functions
 as specified. These tests should treat the proxy as a black box to which an HTTP
  client connects and makes requests. The proxy itself should connect to a running
   Redis instance. The test should test the Redis proxy in its running state (i.e.
    by starting the artifact that would be started in production). It is also expected
 for the test to interact directly with the backing Redis instance in order to get
it into a known good state (e.g. to set keys that would be read back through the proxy).
10. Platform: The software build and tests pass on a modern Linux distribution or Mac OS installation, with the only assumptions being as follows:
               The system has the following software installed:
               The system can access DockerHub over the internet.
11. Single-click build and test: After extracting the source code archive, or 
cloning it from a Git repo, entering the top-level project directory and executing
 will build the code and run all the relevant tests. Apart from the downloading and
manipulation of docker images and containers, no changes are made to the host system 
outside the top- level directory of the project. The build and test should be fully
repeatable and should not require any of software installed on the host system, with
the exception of anything specified explicitly in the requirement.
12. Documentation: The software includes a README file with:
                   High-level architecture overview.
                   What the code does.
                   Algorithmic complexity of the cache operations. Instructions for how to run the proxy and tests.
                   How long you spent on each part of the project.
                   A list of the requirements that you did not implement and the reasons for omitting them.
#### Bonus requirements
13. Parallel concurrent processing: Multiple clients are able to concurrently connect
to the proxy (up to some configurable maximum limit) without adversely impacting the
functional behaviour of the proxy. When multiple clients make concurrent requests to
the proxy, it would execute a number of these requests (up to some configurable limit)
in parallel (i.e. in a way so that one request does not have to wait for another one 
to complete before it starts processing).
14. Redis client protocol: Clients interface to the Redis proxy through a subset of
 the Redis protocol (as opposed to using the HTTP protocol). The proxy should implement
  the parts of the Redis protocol that is required to meet this specification.

## Design

The focus of this design is on implementing the given requirements in a reasonable 
amount of time. Python was chosen as a language to allow efficient use of developer 
time. I have done two implementations of the proxy server. The first one is the HTTP 
proxy server which tries to implement all of the requested requirements. The second is
a TCP server that implements Redis's RESP protocol while implementing the core GET
functionality.

#### HTTP proxy server

I wanted to use a lightweight framework which needs minimal amount of boilerplate
 code to get it up and running. This also makes the code easier to review. The 
HTTP proxy design uses a Python based Flask web server.

![Alt text](redis_http_proxy.png?raw=true "Architectural Diagram: Redis HTTP proxy")
###### Architectural Diagram: Redis HTTP proxy

The request to get a key from Redis is implemented with a HTTP GET on the /get endpoint.
The key is passed via the query param. So, to get a key via cURL, you may do:

```curl localhost:6000/get?key=name```

If a key is not found in Redis, the API returns status code 404. If the key is found 
in LRU (cache hit), the API return code 200. Otherwise, for a cache miss on the LRU and when
 the key exists in Redis, the API returns code 201.

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

Since this is a bonus task, I used the standard socketserver library in python
to create a barebones TCP server. The processing of the RESP protocol was the business
logic that I wanted to spend my time on.

![Alt text](Redis_RESP_proxy.png?raw=true "Architectural Diagram: Redis RESP proxy")
###### Architectural Diagram: Redis RESP proxy

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

In order to serve multiple connections efficiently, connection pooling with a 
configurable number of maximum connections is used. Redis's python client provides
a simple way of creating the pool. It then transparently leases/ puts back connections
to the pool as requests are made.

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

I have managed to implement all the requirements. 
In order to finish my tasks on time, I categorized the various requirements into 3 buckets:
1. Most Important: Configuration, HTTP proxy, LRU with capacity, End to end API tests
2. Good to have: LRU cache expiry, sequential processing
3. Least Important: Concurrent processing, RESP proxy implementation

I was able to add tests for almost all the requirements except for sequential and 
 concurrent processing tasks. Here, I was having difficulty implementing a reliable unit test.
This is the breakdown of the amount of time I spent on various tasks.

HTTP service + Single backing Redis instance + Configuration: 1 hours

Global expiry: 0.5 hours

Cached get + LRU eviction + Fixed key size: 1.5 hours

Sequential + Concurrent processing: 1 hour, 

Tests: 1 hours

RESP protocol: 1 hours

## Software Requirements

docker-compose >= 1.25.5 (This is primarily for the --env-file option 
which is not present on older docker-compose binaries)

python3 (for the unit tests. Did not add backward compatability for python2 as it is EOL now)
