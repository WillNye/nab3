import logging

from nab3.mixin import MetricMixin, SecurityGroupMixin
from nab3.base import PaginatedBaseService

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class TargetGroup(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_target_groups
    """
    boto3_client_name = 'elbv2'
    key_prefix = 'TargetGroup'
    _boto3_describe_def = dict(
        call_params=dict(
            load_balancer=dict(name='LoadBalancerArn', type=str),
            arn=dict(name='TargetGroupArns', type=list),  # list<str>,
            name=dict(name='Names', type=list),  # list<str>
        )
    )


class LoadBalancer(MetricMixin, SecurityGroupMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """
    boto3_client_name = 'elbv2'
    key_prefix = 'LoadBalancer'
    _boto3_describe_def = dict(
        call_params=dict(
            arn=dict(name='LoadBalancerArns', type=list),  # list<str>
            name=dict(name='Names', type=list),  # list<str>
        )
    )
    _boto3_response_override = dict(DNSName='dns_name')

    @property
    def _stat_dimensions(self) -> list:
        stat_id = self.arn.split(':loadbalancer/')[-1]
        return [dict(Name='LoadBalancer', Value=stat_id)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ApplicationELB'


class LoadBalancerClassic(MetricMixin, SecurityGroupMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """
    boto3_client_name = 'elb'
    key_prefix = 'LoadBalancer'
    _boto3_describe_def = dict(
        client_call='describe_load_balancers',
        call_params=dict(
            name=dict(name='LoadBalancerNames', type=list)  # list<str>
        ),
        response_key='LoadBalancerDescriptions'
    )
    _boto3_response_override = dict(DNSName='dns_name')

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='LoadBalancerName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ELB'

