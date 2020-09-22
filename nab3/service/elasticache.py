import logging

from nab3.mixin import MetricMixin, SecurityGroupMixin
from nab3.base import PaginatedBaseService
from nab3.utils import snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class ElasticacheCluster(MetricMixin, SecurityGroupMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_cache_clusters
    """
    boto3_client_name = 'elasticache'
    key_prefix = 'Cache'
    _to_boto3_case = snake_to_camelcap
    _boto3_describe_def = dict(
        client_call='describe_cache_clusters',
        call_params=dict(
            id=dict(name='CacheClusterId', type=str),
            show_node_info=dict(name='ShowCacheNodeInfo', type=bool, default=True)
        ),
        response_key='CacheClusters'
    )
    _response_alias = dict(nodes='elasticache_node')
    _boto3_response_override = dict(CacheClusterId='id',
                                    CacheClusterCreateTime='create_time',
                                    CacheClusterStatus='status')

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='CacheClusterId', Value=self.id)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ElastiCache'


class ElasticacheNode(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_reserved_cache_nodes
    """
    boto3_client_name = 'elasticache'
    key_prefix = 'CacheNode'
    _to_boto3_case = snake_to_camelcap
    _boto3_describe_def = dict(
        client_call='describe_reserved_cache_nodes',
        call_params=dict(
            id=dict(name='ReservedCacheNodeId', type=str),
            offering_id=dict(name='ReservedCacheNodesOfferingId', type=str),
            type=dict(name='CacheNodeType', type=str),
            duration=dict(name='Duration', type=str),
            product_description=dict(name='ProductDescription', type=str),
            offering_type=dict(name='OfferingType', type=str),

        ),
        response_key='ReservedCacheNodes'
    )
    _boto3_response_override = dict(ReservedCacheNodeId='id', ReservedCacheNodesOfferingId='offering_id')

