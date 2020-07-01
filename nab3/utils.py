import re


def camel_to_snake(str_obj):
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()


def camel_to_kebab(str_obj):
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', str_obj).lower()


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
