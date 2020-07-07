import asyncio
import concurrent.futures
import re
from functools import partial


def camel_to_snake(str_obj):
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()


def camel_to_kebab(str_obj):
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', str_obj).lower()


def snake_to_camelback(str_obj):
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), str_obj)


def paginated_search(search_fnc, search_kwargs, response_key, max_results=None):
    """Retrieve and aggregate each paged response, returning a single list of each response object
    :param search_fnc:
    :param search_kwargs:
    :param response_key:
    :param max_results:
    :return:
    """
    results = []

    while True:
        response = search_fnc(**search_kwargs)
        results += response[response_key]
        search_kwargs['NextToken'] = response.get('NextToken')

        if search_kwargs['NextToken'] is None or (max_results and len(results) >= max_results):
            return results


def async_describe(search_fnc, id_key, id_list, search_kwargs, chunk_size=50, loop=asyncio.get_event_loop()):
    async def describe(chunked_requests):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    partial(
                        search_fnc,
                        **{id_key: chunked_request},
                        **search_kwargs
                    )
                ) for chunked_request in chunked_requests]

            return [await f for f in asyncio.as_completed(futures)]

    if len(id_list) <= chunk_size:
        return [search_fnc(**{**{id_key: id_list}, **search_kwargs})]

    return loop.run_until_complete(describe([id_list[x:x+chunk_size] for x in range(0, len(id_list), chunk_size)]))
