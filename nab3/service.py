import asyncio
import logging
from itertools import chain
from datetime import datetime as dt, timedelta

from nab3.base import BaseService
from nab3.utils import paginated_search, snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class Alarm(BaseService):
    boto3_service_name = 'cloudwatch'
    client_id = 'Alarm'

    @classmethod
    def get_history(cls, start_date, end_date, name=None, item_type=None, alarm_types=[], sort_descending=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param name: AlarmName='string'
        :param item_type: HistoryItemType='ConfigurationUpdate'|'StateUpdate'|'Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm'|'MetricAlarm']
        :param sort_descending: bool -> ScanBy='TimestampDescending'|'TimestampAscending'
        :return:
        """
        search_kwargs = dict(StartDate=start_date, EndDate=end_date,
                             AlarmTypes=alarm_types,
                             ScanBy='TimestampDescending' if sort_descending else 'TimestampAscending')
        if name:
            search_kwargs['AlarmName'] = name
        if item_type:
            search_kwargs['HistoryItemType'] = item_type

        search_fnc = cls._client.get(cls.boto3_service_name).describe_alarm_history
        results = paginated_search(search_fnc, search_kwargs, 'AlarmHistoryItems')
        return [cls(_loaded=True, **result) for result in results]


class Metric(BaseService):
    boto3_service_name = 'cloudwatch'
    client_id = 'Metric'

    @classmethod
    def get_statistics(cls, namespace, metric_name, start_time, end_time, interval_as_seconds, **kwargs):
        """
        boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics
        docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#dimension-combinations
        Optional params:
            Dimensions=[
                {
                    'Name': 'string',
                    'Value': 'string'
                },
            ],
            StartTime=datetime(2015, 1, 1),
            EndTime=datetime(2015, 1, 1),
            Period=123,
            (Statistics=[
                'SampleCount'|'Average'|'Sum'|'Minimum'|'Maximum',
            ],
            ExtendedStatistics=[
                'string',
            ]) - Statistics or ExtendedStatistics must be set ,
            Unit='Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|'Kilobytes'|'Megabytes'|'
        :param namespace:
        :param metric_name:
        :param start_time:
        :param end_time:
        :param interval_as_seconds: This is the Period paremeter. Renamed here to make the purpose more intuitive
        :param kwargs:
        :return:
        """
        search_kwargs = dict(EndTime=end_time,
                             Namespace=namespace,
                             MetricName=metric_name,
                             Period=interval_as_seconds,
                             StartTime=start_time)
        for k, v in kwargs.items():
            search_kwargs[snake_to_camelcap(k)] = v

        client = cls._client.get(cls.boto3_service_name)
        response = client.get_metric_statistics(**search_kwargs)
        return [cls(_loaded=True, **obj) for obj in response.get('Datapoints', [])]

    @classmethod
    def get(cls, loop=asyncio.get_event_loop(), **kwargs):
        raise NotImplementedError("get is not a supported operation for Metric")

    @classmethod
    def load(cls, **kwargs):
        raise NotImplementedError("load is not a supported operation for Metric")

    @classmethod
    def list(cls, **kwargs) -> list:
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.list_metrics, kwargs, f"{cls.client_id}s")
        return [cls(_loaded=True, **obj) for obj in response]


class AutoScalePolicy(BaseService):
    boto3_service_name = 'autoscaling'
    client_id = 'Policy'

    def get_alerts(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate'|'StateUpdate'|'Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm'|'MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending'|'TimestampAscending'
        :return:
        """
        alerts = []
        alert_obj = self._get_service_class('alarm')

        for alert in self.alarms:
            alerts += alert_obj.get_history(name=alert.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alerts

    def _load(self):
        response = self.client.describe_policies(
            PolicyNames=[self.name]
        )['ScalingPolicies']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def list(cls, asg_name=None, policy_names=[], policy_types=[]):
        search_kwargs = dict(PolicyNames=policy_names, PolicyTypes=policy_types)
        if asg_name:
            search_kwargs['AutoScalingGroupName'] = asg_name

        search_fnc = cls._client.get(cls.boto3_service_name).describe_policies
        results = paginated_search(search_fnc, search_kwargs, 'ScalingPolicies')
        return [cls(_loaded=True, **result) for result in results]


class AppAutoScalePolicy(BaseService):
    boto3_service_name = 'application-autoscaling'
    client_id = 'Policy'

    def get_alerts(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate'|'StateUpdate'|'Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm'|'MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending'|'TimestampAscending'
        :return:
        """
        alerts = []
        alert_obj = self._get_service_class('alarm')

        for alert in self.alarms:
            alerts += alert_obj.get_history(name=alert.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alerts

    def _load(self):
        response = self.client.describe_scaling_policies(
            ServiceNamespace=self.service_namespace,
            ResourceId=self.resource_id
        )['ScalingPolicies']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def list(cls, service_namespace, resource_id=None):
        search_kwargs = dict(ServiceNamespace=service_namespace)
        if resource_id:
            search_kwargs['ResourceId'] = resource_id

        search_fnc = cls._client.get(cls.boto3_service_name).describe_scaling_policies
        results = paginated_search(search_fnc, search_kwargs, 'ScalingPolicies')
        return [cls(_loaded=True, **result).load() for result in results]


class AppService(BaseService):
    _auto_scale_policies: list = None

    @property
    def resource_id(self):
        raise NotImplementedError

    @property
    def scaling_policies(self):
        if self._auto_scale_policies is None:
            asp = self._get_service_class('app_scaling_policy')
            asp_list = asp.list(service_namespace=self.boto3_service_name, resource_id=self.resource_id)
            self._auto_scale_policies = asp_list

        return self._auto_scale_policies


class AutoScaleService(BaseService):
    _auto_scale_policies: list = None

    @property
    def scaling_policies(self):
        if self._auto_scale_policies is None:
            asp = self._get_service_class('scaling_policy')
            asp_list = asp.list(self.name)
            self._auto_scale_policies = asp_list

        return self._auto_scale_policies


class MetricService(BaseService):
    _available_metrics = None

    def get_statistics(self,
                    metric_name: str,
                    start_time: dt = dt.utcnow()-timedelta(hours=3),
                    end_time: dt = dt.utcnow(),
                    interval_as_seconds: int = 300, **kwargs) -> list:
        """
        :param metric_name:
        :param start_time:
        :param end_time:
        :param interval_as_seconds:
        :param kwargs:
        :return:
        """
        kwargs = {snake_to_camelcap(k): v for k, v in kwargs}
        dimensions = self._stat_dimensions + kwargs.get('Dimensions', [])
        kwargs['Dimensions'] = dimensions

        if kwargs.get('ExtendedStatistics') is None and kwargs.get('Statistics') is None:
            LOGGER.warning('Neither ExtendedStatistics or Statistics was set. Defaulting to Statistics=[Average]')
            kwargs['Statistics'] = ['Average']

        metric_cls = self._get_service_class('metric')
        metrics = metric_cls.get_statistics(
            self._stat_name, metric_name, start_time, end_time, interval_as_seconds, **kwargs
        )
        return metrics

    @property
    def available_metrics(self):
        if self._available_metrics is None:
            metrics = self._get_service_class('metric')
            metrics = metrics.list(Namespace=self._stat_name, Dimensions=self._stat_dimensions)
            self._available_metrics = metrics

        return self._available_metrics

    @property
    def metric_options(self):
        if self._available_metrics is None:
            metrics = self._get_service_class('metric')
            metrics = metrics.list(Namespace=self._stat_name, Dimensions=self._stat_dimensions)
            self._available_metrics = metrics

        return set(metric.name for metric in self._available_metrics)

    @property
    def _stat_dimensions(self) -> list:
        raise NotImplementedError

    @property
    def _stat_name(self) -> str:
        """
        docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/aws-services-cloudwatch-metrics.html
        :return:
        """
        raise NotImplementedError


class SecurityGroup(BaseService):
    boto3_service_name = 'ec2'
    client_id = 'SecurityGroup'
    key_prefix = 'Group'
    _service_list_map = dict(user_id_group_pairs='security_group')
    _accessible_sg = None

    def _load(self):
        group_id = getattr(self, 'id', None)
        group_name = getattr(self, 'name', None)
        if not group_id and not group_name:
            raise AttributeError('id or name must be set for load to be called')

        group_names = [group_name] if group_name else []
        group_ids = [group_id] if group_id else []
        response = self.client.describe_security_groups(
            GroupIds=group_ids,
            GroupNames=group_names
        )[f'{self.client_id}s']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def get(cls, sg_id=None, sg_name=None):
        """
        :param sg_id:
        :param sg_name:
        :return: SecurityGroup()
        """
        obj = cls(id=sg_id, name=sg_name)
        obj.load()
        return obj

    @classmethod
    def list(cls, loop=asyncio.get_event_loop(), **kwargs):
        """
        For list of accepted kwarg values:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param loop: Optionally pass an event loop
        :param kwargs:
        :return:
        """
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.describe_security_groups, kwargs, f"{cls.client_id}s")
        return [cls(_loaded=True, **obj) for obj in response]


class LaunchConfiguration(BaseService):
    boto3_service_name = 'autoscaling'
    client_id = 'LaunchConfiguration'

    def _load(self):
        response = self.client.describe_launch_configurations(
            LaunchConfigurationNames=[self.name],
            MaxRecords=1
        )[f'{self.client_id}s']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self


class LoadBalancer(BaseService):
    boto3_service_name = 'elbv2'
    client_id = 'LoadBalancer'

    def _load(self):
        pass


class EC2Instance(BaseService):
    boto3_service_name = 'ec2'
    client_id = 'Instance'

    @classmethod
    def list(cls, instance_ids=[], filters=[]) -> list:
        """
        boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances

        :param instance_ids: list<str>
        :param filters: list<dict> Available filter options available in the boto3 link above
        :return:
        """
        search_fnc = cls._client.get(cls.boto3_service_name).describe_instances
        search_kwargs = dict(Filters=filters, InstanceIds=instance_ids)
        results = paginated_search(search_fnc, search_kwargs, 'Reservations')
        instances = list(chain.from_iterable([obj['Instances']] for obj in results))
        return [cls(_loaded=True, **result) for result in instances]

    def _load(self):
        response = self.client.describe_instances(InstanceIds=[self.id])
        response = response.get('Reservations', [])
        if response:
            for k, v in response[0].get('Instances', {})[0].items():
                self._set_attr(k, v)

        return self


class ASG(AutoScaleService):
    boto3_service_name = 'autoscaling'
    client_id = 'AutoScalingGroup'
    _security_groups = None
    _accessible_resources = None

    def _load(self):
        response = self.client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.name]
        )[f'{self.client_id}s']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @property
    def security_groups(self):
        if self._security_groups is None:
            try:
                l_config = self.launch_configuration.load()
                self._security_groups = [sg.load() for sg in l_config.security_groups]
            except AttributeError:
                self._security_groups = []
        return self._security_groups

    @property
    def accessible_resources(self):
        if self._accessible_resources is None:
            filter_list = [sg.id for sg in self.security_groups]
            if not filter_list:
                self._accessible_resources = []
                return self._accessible_resources

            instance_obj = self._get_service_class('security_group')
            self._accessible_resources = instance_obj.list(Filters=[dict(
                Name='ip-permission.group-id',
                Values=filter_list
            )])

        return self._accessible_resources

    @classmethod
    def list(cls, loop=asyncio.get_event_loop(), **kwargs):
        """
        For list of accepted kwarg values:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param loop: Optionally pass an event loop
        :param kwargs:
        :return:
        """
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.describe_auto_scaling_groups, kwargs, f"{cls.client_id}s")
        return [cls(_loaded=True, **obj) for obj in response]


class ECSTask(BaseService):
    boto3_service_name = 'ecs'
    client_id = 'task'

    def _load(self):
        response = self.client.describe_tasks(
            cluster=self.cluster,
            tasks=[self.id]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def get(cls, id, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param id: string The task instance ID
        :return:
        """
        return cls(id=id, cluster=cluster_name).load()

    @classmethod
    def list(cls, cluster_name, loop=asyncio.get_event_loop(), **kwargs):
        """
        For list of accepted kwarg values:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param loop: Optionally pass an event loop
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return cls._list(describe_kwargs=dict(cluster=cluster_name), loop=loop, **kwargs)


class ECSService(AppService, MetricService):
    boto3_service_name = 'ecs'
    client_id = 'service'
    _cluster = None

    def _load(self):
        response = self.client.describe_services(
            cluster=self.cluster,
            services=[self.name]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @property
    def cluster(self):
        if self._cluster is None:
            self.load()
            self._cluster = self.cluster_arn.split('/')[-1]

        return self._cluster

    @property
    def resource_id(self):
        return f"{self.client_id}/{self.cluster}/{self.name}"

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='ClusterName', Value=self.cluster), dict(Name='ServiceName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ECS'

    @classmethod
    def get(cls, name, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param name: string The name of the service
        :return:
        """
        return cls(name=name, cluster=cluster_name).load()

    @classmethod
    def list(cls, cluster_name, loop=asyncio.get_event_loop(), **kwargs):
        """
        For list of accepted kwarg values:
        https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param loop: Optionally pass an event loop
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return cls._list(describe_kwargs=dict(cluster=cluster_name), loop=loop, **kwargs)


class ECSInstance(BaseService):
    boto3_service_name = 'ecs'
    client_id = 'containerInstance'

    def _load(self):
        response = self.client.describe_container_instances(
            cluster=self.cluster,
            containerInstances=[self.id]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def get(cls, id, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param id: string The Container instance ID
        :return:
        """
        return cls(id=id, cluster=cluster_name).load()

    @classmethod
    def list(cls, cluster_name, loop=asyncio.get_event_loop(), **kwargs):
        """
        For list of accepted kwarg values:
        https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param loop: Optionally pass an event loop
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return cls._list(describe_kwargs=dict(cluster=cluster_name), loop=loop, **kwargs)


class ECSCluster(AutoScaleService, MetricService):
    boto3_service_name = 'ecs'
    client_id = 'Cluster'
    _instances = None
    _services = None

    def _load(self):
        """

        :param options: list<`ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'>
        :return:
        """
        response = self.client.describe_clusters(
            clusters=[self.name],
            include=self._options
        )['clusters']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @property
    def instances(self):
        if self._instances is None:
            instance_obj = self._get_service_class('ecs_instance')
            self._instances = instance_obj.list(self.name)

        return self._instances

    @property
    def services(self):
        if self._services is None:
            instance_obj = self._get_service_class('ecs_service')
            self._services = instance_obj.list(self.name)

        return self._services

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='ClusterName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ECS'

    @classmethod
    def get(cls, name, options=['ATTACHMENTS', 'STATISTICS', 'SETTINGS']):
        """Hits the client to set the entirety of the object using the provided lookup field.

        Default filter field is normally name

        :param name:
        :param options: list<`ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'>
        :return:
        """
        return cls(name=name, _options=options).load()
