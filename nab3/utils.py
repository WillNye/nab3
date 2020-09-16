import asyncio
import re


def camel_to_snake(str_obj: str) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()


def camel_to_kebab(str_obj: str) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', str_obj).lower()


def snake_to_camelback(str_obj: str) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), str_obj)


def snake_to_camelcap(str_obj: str) -> str:
    str_obj = camel_to_snake(str_obj).title()  # normalize string and add required case convention
    return str_obj.replace('_', '')  # Remove underscores


def paginated_search(search_fnc, search_kwargs: dict, response_key: str, max_results: int = None) -> list:
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
        results += response.get(response_key, [])
        search_kwargs['NextToken'] = response.get('NextToken')

        if search_kwargs['NextToken'] is None or (max_results and len(results) >= max_results):
            return results


async def describe_resource(search_fnc, id_key: str, id_list: list, search_kwargs: dict, chunk_size: int = 50) -> list:
    """Chunks up describe operation and runs requests concurrently.

    :param search_fnc: Name of the boto3 function e.g. describe_auto_scaling_groups
    :param id_key: Name of the key used for describe operation e.g. AutoScalingGroupNames
    :param id_list: List of id values
    :param search_kwargs: Additional arguments to pass to the describe operation like Filter, MaxRecords, or Tags
    :param chunk_size: Used to set request size. Cannot exceed the operation's MaxRecords or there may be data loss.
    :return: list<boto3 describe response>
    """
    async def _describe(chunked_list):
        return search_fnc(**{**{id_key: chunked_list}, **search_kwargs})

    if len(id_list) <= chunk_size:
        return [search_fnc(**{**{id_key: id_list}, **search_kwargs})]

    return await asyncio.gather(*[_describe(id_list[x:x+chunk_size]) for x in range(0, len(id_list), chunk_size)])
