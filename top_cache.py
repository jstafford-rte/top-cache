# coding=utf-8
from django.conf import settings
from django.core.cache import cache
from functools import wraps
import hashlib
import datetime

__author__ = 'John Stafford'
__copyright__ = 'Copyright (c) Raidió Teilifís Éireann'

__licence__ = '3-clause BSD'
__version__ = '1.0.0'
__email__ = 'john.stafford@rte.ie'
__status__ = 'Production'

DEFAULT_TIMEOUT = 60 * 3
MINT_DELAY = settings.MINT_DELAY if hasattr(settings, 'MINT_DELAY') else 30

def set(cache_key, value, timeout=DEFAULT_TIMEOUT, refreshed=False):
    """
    Persists data to the cache
    :param cache_key: Unique identifier for the data to be persisted to cache
    :type cache_key: str or unicode
    :param value: Data to be persisted to cache
    :param timeout: (Optional) Duration for which data is to be persisted, defaults to DEFAULT_TIMEOUT seconds
    :type timeout: int
    :param refreshed: (Optional) Specifies if data has been persisted beyond its original duration, defaults to False
    :type refreshed: bool
    """
    refresh_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    mint_timeout = timeout + MINT_DELAY
    packed_value = (value, refresh_time, refreshed)
    return cache.set(cache_key, packed_value, mint_timeout)

def get(cache_key):
    """
    Retrieves data from the cache
    :param cache_key: The key for a cached value
    :type cache_key: str or unicode
    """
    packed_value = cache.get(cache_key)
    if not packed_value:
        return None
    value, refresh_time, refreshed = packed_value
    if (datetime.datetime.now() > refresh_time) and not refreshed:
        # Store the stale value while the cache revalidates for another
        # MINT_DELAY seconds.
        set(cache_key, value, timeout=MINT_DELAY, refreshed=True)
        return None
    return value

def top_cache(timeout=DEFAULT_TIMEOUT, decorates_method=False):
    """
    Decorator to cache function and method calls
    Optional timeout parameter - defaults to 3 minutes
    :param timeout: (Optional) Specifies cache timeout in seconds, defaults to DEFAULT_TIMEOUT seconds
    :type timeout: int
    :param decorates_method: (Optional) Specifies if top_cache decorates a class method, defaults to False
    :type decorates_method: bool

    Use example - cache my_func for 15 minutes:
    @top_cache(timeout=60 * 15)
    def my_func(*args, **kwargs):
        ...
    """
    def cache_request_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            """
            Returns cached data if it exists, otherwise executes
            wrapped function/method call and caches returned values
            """
            # Buld cache key from function name and parameters
            cache_key = func.__name__
            # Use args to continue building cache key
            cache_key_args = args

            if args and decorates_method:
                # Adds class name from the 'self' arg specified first by methods to the cache key
                class_name = args[0].__class__.__name__
                cache_key = '{0}_{1}'.format(class_name, cache_key)
                cache_key_args = cache_key_args[1:]

            for arg in cache_key_args:
                cache_key = '{0}_{1}'.format(cache_key, arg)
            # Use kwargs to continue building cache key
            for key, value in kwargs.items():
                cache_key = '{0}_{1}={2}'.format(cache_key, key, value)

            # Hash cache key to prevent illegal characters or excessive key length
            cache_key = hashlib.md5(cache_key).hexdigest()
            rtn = get(cache_key)
            if rtn:
                return rtn
            rtn = func(*args, **kwargs)
            set(cache_key, rtn, timeout=timeout)
            return rtn
        return func_wrapper
    return cache_request_decorator
