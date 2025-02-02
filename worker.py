import os
from redis import Redis
from rq import Worker, Queue, Connection

# Get the Redis URL from environment variables
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)

listen = ['default']

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
