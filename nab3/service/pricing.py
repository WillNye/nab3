import json
import logging

from nab3.base import PaginatedBaseService

from nab3.utils import (
    camel_to_snake, paginated_search, snake_to_camelcap
)

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class Pricing(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/pricing.html#Pricing.Client.get_products
    """
    boto3_client_name = 'pricing'
    key_prefix = 'product'
    _to_boto3_case = snake_to_camelcap
    _boto3_describe_def = dict(
        client_call='get_products',
        call_params=dict(
            filters=dict(name='Filters', type=list),  # list<dict(Type=str, Field=any, Value=any)>
            service_code=dict(name='ServiceCode', type=str)
        ),
        response_key='PriceList'
    )

    def get_on_demand_hourly(self, currency='usd'):
        pricing = list(list(self.on_demand.values())[0]["price_dimensions"].values())[0]
        return float(pricing['price_per_unit'][currency])

    def get_on_demand_monthly(self, currency='usd'):
        return self.get_on_demand_hourly(currency) * 24 * 30

    @classmethod
    async def _list(cls, **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org
        :param kwargs:
        :return: list<cls()>
        """
        kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.items() if k not in ['list_kwargs', 'describe_kwargs']}
        response_key = cls._boto3_describe_def.get('response_key', f'{cls.key_prefix}s')
        fnc_base = camel_to_snake(cls.key_prefix)
        fnc_name = cls._boto3_describe_def.get('client_call', f'describe_{fnc_base}s')
        return_val = []

        client = cls._client.get(cls.boto3_client_name)
        boto3_fnc = getattr(client, fnc_name)
        response = paginated_search(boto3_fnc, kwargs, response_key)
        for obj in response:
            loaded_obj = json.loads(obj)
            attributes = loaded_obj['product']['attributes']
            for k, v in attributes.items():
                if attributes[k] == 'Yes':
                    attributes[k] = True
                elif attributes[k] == 'No':
                    attributes[k] = False

            return_val.append(dict(**loaded_obj['terms'], **attributes))

        return [cls(_loaded=True, **obj) for obj in return_val]
