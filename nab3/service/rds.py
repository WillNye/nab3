import logging

from nab3.mixin import MetricMixin
from nab3.base import PaginatedBaseService
from nab3.utils import snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class RDSCluster(MetricMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_clusters
    """
    boto3_client_name = 'rds'
    key_prefix = 'DBCluster'
    _to_boto3_case = snake_to_camelcap
    _boto3_response_override = dict(DBClusterIdentifier='id', DbClusterResourceId='resource_id')
    _response_alias = dict(members='rds_instance')
    _boto3_describe_def = dict(
        client_call='describe_db_clusters',
        call_params=dict(
            id=dict(name='db_cluster_identifier', type=str),
            filters=dict(name='filters', type=list)
        ),
        response_key='DBClusters'
    )
    """
    Details for the filters describe kwarg
    Structure: list(dict(Name:str, Values:list))

    Supported filters per boto3:    
    db-cluster-id - Accepts DB cluster identifiers and DB cluster Amazon Resource Names (ARNs). The results list will only include information about the DB clusters identified by these ARNs.

    The following actions can be filtered:    
    DescribeDBClusterBacktracks
    DescribeDBClusterEndpoints
    DescribeDBClusters
    DescribeDBInstances
    DescribePendingMaintenanceActions
    """

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='DBClusterIdentifier', Value=self.id)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/RDS'


class RDSInstance(MetricMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_instances
    """
    boto3_client_name = 'rds'
    key_prefix = 'DBInstance'
    _to_boto3_case = snake_to_camelcap
    _boto3_response_override = dict(DBInstanceIdentifier='id')
    _boto3_describe_def = dict(
        client_call='describe_db_instances',
        call_params=dict(
            id=dict(name='db_instance_identifier', type=str),
            filters=dict(name='filters', type=list)
        ),
        response_key='DBInstances'
    )
    """
    Details for the filters describe kwarg
    Structure: list(dict(Name:str, Values:list))

    Supported filters per boto3:    
        db-cluster-id - Accepts DB cluster identifiers and DB cluster Amazon Resource Names (ARNs). The results list will only include information about the DB instances associated with the DB clusters identified by these ARNs.
        db-instance-id - Accepts DB instance identifiers and DB instance Amazon Resource Names (ARNs). The results list will only include information about the DB instances identified by these ARNs.
        dbi-resource-id - Accepts DB instance resource identifiers. The results list will only include information about the DB instances identified by these DB instance resource identifiers.
        domain - Accepts Active Directory directory IDs. The results list will only include information about the DB instances associated with these domains.
        engine - Accepts engine names. The results list will only include information about the DB instances for these engines.
    """

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='DBInstanceIdentifier', Value=self.id)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/RDS'
