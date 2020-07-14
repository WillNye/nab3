import asyncio
import concurrent.futures
import copy
import inspect
import logging
import re
from itertools import chain

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


def camel_to_snake(str_obj) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()


def camel_to_kebab(str_obj) -> str:
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', str_obj).lower()


def snake_to_camelback(str_obj) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), str_obj)


def snake_to_camelcap(str_obj) -> str:
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


async def describe(search_fnc, id_key: str, id_list: list, search_kwargs: dict, chunk_size: int = 50):
    async def _describe(chunked_list):
        return search_fnc(**{**{id_key: chunked_list}, **search_kwargs})

    if len(id_list) <= chunk_size:
        return [search_fnc(**{**{id_key: id_list}, **search_kwargs})]

    return await asyncio.gather(*[_describe(id_list[x:x+chunk_size]) for x in range(0, len(id_list), chunk_size)])


class Filter:

    def __init__(self, **kwargs):
        self.filter_params = kwargs

    def filter(self, **kwargs):
        for k, v in kwargs.items():
            self.filter_params[k] = v
        return self

    async def _match(self, service_obj, param_as_list, filter_value) -> tuple:
        """

        :param service_obj:
        :param param_as_list:
        :param filter_value:
        :return:
        """
        is_match = False
        safe_params = copy.deepcopy(param_as_list)  # Cause safety first
        if len(safe_params) > 1:
            if isinstance(service_obj, list):
                hits = await asyncio.gather(*[
                    self._match(e, safe_params, filter_value) for e in service_obj
                ])
                if any(hit[1] for hit in hits):
                    # If 1 gets in they all get in because this indicates the primary object is a match
                    response, is_match = [hit[0] for hit in hits], True
                else:
                    response, is_match = [], False
            elif service_obj:
                cur_key = safe_params.pop(0)
                if isinstance(service_obj, dict):
                    obj_val = service_obj.get(cur_key)
                    response, is_match = await self._match(obj_val, safe_params, filter_value)
                    if is_match:
                        service_obj[cur_key] = response
                elif inspect.isclass(type(service_obj)):
                    try:
                        await service_obj.load()
                        if cur_key in service_obj.__dict__:
                            nested_obj = getattr(service_obj, cur_key, None)
                        else:
                            nested_obj = await getattr(service_obj, cur_key, None)
                        response, is_match = await self._match(nested_obj, safe_params, filter_value)
                        if is_match:
                            setattr(service_obj, cur_key, response)
                    except AttributeError as ae:
                        LOGGER.warning(f'Await Service Object Error {ae} {service_obj} {cur_key} {safe_params}')

            return service_obj, is_match
        else:
            operation = safe_params[0]
            try:
                """ToDo:
                # list_any
                # list_all
                # exact
                # iexact
                # lt
                # gt
                # lte
                # gte
                """
                if service_obj is None:
                    return service_obj, False
                elif operation == 're':
                    return service_obj, bool(re.match(filter_value, service_obj))
                else:
                    raise KeyError(f'{operation} is not a valid Filter operation.\nOptions: {self.get_operations()}')
            except Exception as e:
                LOGGER.warning(str(e))
                return service_obj, False

    async def run(self, service_objects):
        for filter_param, filter_value in self.filter_params.items():
            hits = await asyncio.gather(*[
                self._match(so, filter_param.split('__'), filter_value) for so in service_objects
            ])
            service_objects = [hit[0] for hit in hits if hit[1]]
        return service_objects

    @staticmethod
    def get_operations():
        return ['re']
