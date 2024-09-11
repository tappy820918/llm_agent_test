import pickle

import redis
import json
import functools
import os

from llm_agent.src.utils import Member

# Connect to Redis server
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_DB = os.getenv('REDIS_DB', 0)
REDIS_CACHE_TTL = os.getenv('REDIS_CACHE_TTL', 2*24*60*60) # 2 days in seconds

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def redis_cache(ttl=REDIS_CACHE_TTL):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a unique key based on the function name and its arguments
            key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            # Check if the result is already cached in Redis
            cached_result = redis_client.get(key)
            if cached_result:
                return json.loads(cached_result)
            # Call the function and cache the result
            result = func(*args, **kwargs)
            redis_client.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

def redis_cache_pkl(ttl=REDIS_CACHE_TTL):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a unique key based on the function name and its arguments
            key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            # Check if the result is already cached in Redis
            cached_result = redis_client.get(key)
            if cached_result:
                return pickle.loads(cached_result)
            # Call the function and cache the result
            result = func(*args, **kwargs)
            redis_client.setex(key, ttl, pickle.dumps(result))
            return result
        return wrapper
    return decorator

def redis_member_ver_cache(ttl=REDIS_CACHE_TTL):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a unique key based on the function name and its arguments
            if len(args) < 3:
                raise ValueError("Function requires at least 2 arguments")
            if not isinstance(args[1], Member):
                raise ValueError("First argument should be of type Member")
            member_str = f"{func.__name__}:{args[1].model_dump_json()}"
            version = f"{func.__name__}:{args[2]}"
            key = f"{func.__name__}:{member_str}:{version}:{json.dumps(kwargs)}"
            # Check if the result is already cached in Redis
            cached_result = redis_client.get(key)
            if cached_result:
                return pickle.loads(cached_result)
            # Call the function and cache the result
            result = func(*args, **kwargs)
            redis_client.setex(key, ttl, pickle.dumps(result))
            return result
        return wrapper
    return decorator
