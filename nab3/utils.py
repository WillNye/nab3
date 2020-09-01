import asyncio
import re


def camel_to_snake(str_obj: str) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()


def camel_to_kebab(str_obj: str) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', str_obj).lower()


def snake_to_camelback(str_obj: str) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), str_obj)


def snake_to_camelcap(str_obj: str) -> str:
    return snake_to_camelback(str_obj).title()


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


async def describe_resource(search_fnc, id_key: str, id_list: list, search_kwargs: dict, chunk_size: int = 50):
    async def _describe(chunked_list):
        return search_fnc(**{**{id_key: chunked_list}, **search_kwargs})

    if len(id_list) <= chunk_size:
        return [search_fnc(**{**{id_key: id_list}, **search_kwargs})]

    return await asyncio.gather(*[_describe(id_list[x:x+chunk_size]) for x in range(0, len(id_list), chunk_size)])
