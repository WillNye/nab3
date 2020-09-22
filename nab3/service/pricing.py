import logging

from nab3.base import PaginatedBaseService

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class Pricing(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/pricing.html#Pricing.Client.get_products
    """
    boto3_client_name = 'pricing'
    key_prefix = 'product'
    _boto3_describe_def = dict(
        client_call='get_products',
        call_params=dict(
            filters=dict(name='Filters', type=list),  # list<dict(Type=str, Field=any, Value=any)>
            service_code=dict(name='ServiceCode', type=str)
        ),
        response_key='PriceList'
    )

