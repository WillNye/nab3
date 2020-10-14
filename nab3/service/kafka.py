import asyncio
import logging

from nab3.mixin import MetricMixin
from nab3.base import BaseService, PaginatedBaseService, ServiceWrapper
from nab3.utils import paginated_search, snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class KafkaCluster(MetricMixin, BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kafka.html#Kafka.Client.describe_cluster
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kafka.html#Kafka.Client.list_clusters
    """
    boto3_client_name = 'kafka'
    key_prefix = 'Cluster'
    _to_boto3_case = snake_to_camelcap
    _boto3_describe_def = dict(
        client_call='describe_cluster',
        call_params=dict(
            arn=dict(name='cluster_arn', type=str)
        ),
        response_key='ClusterInfo'
    )
    _boto3_list_def = dict(
        client_call='list_clusters',
        call_params=dict(
            name_prefix=dict(name='cluster_name_filter', type=str)
        ),
        response_key='ClusterInfoList'
    )
    _boto3_response_override = dict(BrokerNodeGroupInfo='broker_summary')

    def __init__(self, **kwargs):
        self.create_service_field('brokers', 'kafka_broker')
        super(self._get_service_class('kafka_cluster'), self).__init__(**kwargs)

    async def get_topics(self) -> list:
        """
        NOTE: this only works if EnhancedMonitoring was set to PER_TOPIC_PER_BROKER when the cluster was created
        :return list:
        """
        resp = getattr(self, 'topics', None)
        if resp:
            return resp
        elif not self.brokers.is_loaded():
            await self.fetch('brokers')

        topics = set()
        broker_topics = await asyncio.gather(*[broker.get_topics() for broker in self.brokers])
        for topic in broker_topics:
            topics.update(topic)

        self.topics = list(topics)
        return self.topics

    async def load_brokers(self, force=False):
        """Retrieves the cluster's brokers.

        stored as the instance attribute `obj.brokers`

        :return: ServiceWrapper(KafkaBroker)
        """
        if self.brokers.is_loaded() and not force:
            return self.brokers

        self.brokers = await self.brokers.list(cluster_arn=self.arn)
        for broker in self.brokers:
            broker.cluster = self.name

        return self.brokers

    @classmethod
    async def list(cls, fnc_name=None, response_key=None, **kwargs) -> ServiceWrapper:
        """Returns an instance for each object

        :param fnc_name:
        :param response_key:
        :param kwargs:
        :return: list<cls()>
        """
        resp = ServiceWrapper(cls)
        service_list = kwargs.pop('service_list', [])
        boto3_params = cls._boto3_list_def['call_params']
        if not fnc_name:
            fnc_name = cls._boto3_list_def['client_call']
            response_key = cls._boto3_list_def['response_key']

        for param_name, param_attrs in boto3_params.items():
            default_val = param_attrs.get('default')
            value_list = [getattr(service, param_name, None) for service in service_list]
            value_list = [v for v in value_list if v]
            kwarg_val = kwargs.pop(param_name, [])
            value_list += kwarg_val if isinstance(kwarg_val, list) else [kwarg_val]

            if default_val:
                kwargs[param_attrs['name']] = default_val

            for value in value_list:
                if value:
                    if param_attrs['type'] == list:
                        value = value if isinstance(value, list) else [value]
                        param_val = kwargs.get(param_attrs['name'], []) + value
                        kwargs[param_attrs['name']] = param_val
                    else:
                        kwargs[param_attrs['name']] = value

        kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.items()}
        client = cls._client.get(cls.boto3_client_name)
        boto3_fnc = getattr(client, fnc_name)
        response = paginated_search(boto3_fnc, kwargs, response_key)
        resp.service = [cls(_loaded=True, **obj) for obj in response]

        return resp

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='Cluster Name', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/Kafka'


class KafkaBroker(MetricMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kafka.html#Kafka.Client.list_nodes
    """
    boto3_client_name = 'kafka'
    key_prefix = 'Node'
    _to_boto3_case = snake_to_camelcap
    _boto3_describe_def = dict(
        client_call='list_nodes',
        call_params=dict(
            cluster_arn=dict(name='ClusterArn', type=str)
        ),
        response_key='NodeInfoList'
    )
    _boto3_response_override = dict(BrokerId='id', AttachedENIId='attached_en_id', ZookeeperNodeInfo='zookeeper_info')

    def __init__(self, **kwargs):
        broker_info = kwargs.pop('BrokerNodeInfo', None)
        if isinstance(broker_info, dict):
            kwargs = {**kwargs, **broker_info}

        super(self._get_service_class('kafka_broker'), self).__init__(**kwargs)

    async def get_topics(self):
        """
        NOTE: this only works if EnhancedMonitoring was set to PER_TOPIC_PER_BROKER when the cluster was created
        :return list:
        """
        resp = getattr(self, 'topics', None)
        if resp:
            return resp

        topics = set()
        metrics = await self.get_available_metrics()
        for metric in metrics:
            topics.update(dimension['value'] for dimension in metric.dimensions if dimension['name'] == 'Topic')

        self.topics = list(topics)
        return self.topics

    @classmethod
    async def get(cls, *args, **kwargs):
        raise NotImplementedError

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='Cluster Name', Value=self.cluster), dict(Name='Broker ID', Value=str(self.id))]

    @property
    def _stat_name(self) -> str:
        return 'AWS/Kafka'
