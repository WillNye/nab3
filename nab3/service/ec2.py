import logging
from itertools import chain

from nab3.mixin import MetricMixin, PricingMixin
from nab3.base import PaginatedBaseService
from nab3.utils import paginated_search, PRICING_REGION_MAP, snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class SecurityGroup(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_security_groups
    """
    boto3_client_name = 'ec2'
    key_prefix = 'SecurityGroup'
    client_id = 'Group'
    _boto3_describe_def = dict(
        client_call="describe_security_groups",
        call_params=dict(
            id=dict(name='GroupIds', type=list),
            name=dict(name='GroupNames', type=list),
        )
    )
    _to_boto3_case = snake_to_camelcap
    _response_alias = dict(user_id_group_pairs='security_group')
    _boto3_response_override = dict(SecurityGroupId='id')


class EC2Instance(PricingMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    """
    boto3_client_name = 'ec2'
    key_prefix = 'Instance'
    _boto3_describe_def = dict(
        call_params=dict(
            id=dict(name='InstanceIds', type=list),
            filters=dict(name='Filters', type=list)  # list<dict(name=str, values=list<str>)>
        )
    )

    @classmethod
    async def _list(cls, filters=[], instance_ids=[], **kwargs) -> list:
        """

        :param instance_ids: list<str>
        :param filters: list<dict> Available filter options available in the boto3 link above
        :return:
        """
        search_kwargs = dict(Filters=filters, InstanceIds=instance_ids)
        search_fnc = cls._client.get(cls.boto3_client_name).describe_instances
        results = paginated_search(search_fnc, search_kwargs, 'Reservations')
        instances = list(chain.from_iterable([obj['Instances'] for obj in results]))
        return [cls(_loaded=True, **result) for result in instances]

    async def _load(self):
        response = self.client.describe_instances(InstanceIds=[self.id])
        response = response.get('Reservations', [])
        if response:
            if len(response) == 1:
                for k, v in response[0].get('Instances', {})[0].items():
                    self._set_attr(k, v)
            else:
                raise ValueError('Response was not unique')

        return self

    @property
    def _pricing_params(self) -> dict:
        os = getattr(self, 'Platform', None)
        return dict(service_code='AmazonEC2',
                    filters=[
                        {'Field': 'tenancy', 'Value': 'shared', 'Type': 'TERM_MATCH'},
                        {'Field': 'operatingSystem', 'Value': os if os else 'Linux', 'Type': 'TERM_MATCH'},
                        {'Field': 'preInstalledSw', 'Value': 'NA', 'Type': 'TERM_MATCH'},
                        {'Field': 'instanceType', 'Value': self.type, 'Type': 'TERM_MATCH'},
                        {'Field': 'location', 'Value': PRICING_REGION_MAP[self.region], 'Type': 'TERM_MATCH'},
                        {'Field': 'capacitystatus', 'Value': 'Used', 'Type': 'TERM_MATCH'}
                        ])
