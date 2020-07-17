import asyncio
import base64
import logging
from itertools import chain
from datetime import datetime as dt, timedelta

from nab3.base import BaseService, PaginatedBaseService
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
    def get(cls, **kwargs):
        raise NotImplementedError("get is not a supported operation for Metric")

    @classmethod
    def load(cls, **kwargs):
        raise NotImplementedError("load is not a supported operation for Metric")

    @classmethod
    async def list(cls, **kwargs) -> list:
        """
        boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.list_metrics
        :param kwargs:
        :return:
        """
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.list_metrics, kwargs, f"{cls.client_id}s")
        return [cls(_loaded=True, **obj) for obj in response]


class AutoScalePolicy(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_policies
    """
    boto3_service_name = 'autoscaling'
    client_id = 'Policy'
    _boto3_describe_def = dict(
        client_call='describe_policies',
        call_params=dict(
            asg_name=dict(name='AutoScalingGroupName', type=str),
            name=dict(name='PolicyNames', type=list),
            type=dict(name='PolicyTypes', type=list)
        ),
        response_key='ScalingPolicies'
    )

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

    # async def _load(self):
    #     response = self.client.describe_policies(
    #         PolicyNames=[self.name]
    #     )['ScalingPolicies']
    #     if response:
    #         for k, v in response[0].items():
    #             self._set_attr(k, v)
    #
    #     return self
    #
    # @classmethod
    # async def list(cls, asg_name=None, policy_names=[], policy_types=[]):
    #     search_kwargs = dict(PolicyNames=policy_names, PolicyTypes=policy_types)
    #     if asg_name:
    #         search_kwargs['AutoScalingGroupName'] = asg_name
    #
    #     search_fnc = cls._client.get(cls.boto3_service_name).describe_policies
    #     results = paginated_search(search_fnc, search_kwargs, 'ScalingPolicies')
    #     return [cls(_loaded=True, **result) for result in results]


class AppAutoScalePolicy(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/application-autoscaling.html#ApplicationAutoScaling.Client.describe_scaling_policies
    """
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

    async def _load(self):
        response = self.client.describe_scaling_policies(
            ServiceNamespace=self.service_namespace,
            ResourceId=self.resource_id
        )['ScalingPolicies']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    async def list(cls, service_namespace, resource_id=None):
        search_kwargs = dict(ServiceNamespace=service_namespace)
        if resource_id:
            search_kwargs['ResourceId'] = resource_id

        search_fnc = await cls._client.get(cls.boto3_service_name).describe_scaling_policies
        results = paginated_search(search_fnc, search_kwargs, 'ScalingPolicies')
        return await asyncio.gather(*[cls(_loaded=True, **result).load() for result in results])


class BaseAppService(BaseService):
    _auto_scale_policies: list = False

    @property
    def resource_id(self):
        raise NotImplementedError

    @property
    async def scaling_policies(self):
        if self._auto_scale_policies is False:
            asp = self._get_service_class('app_scaling_policy')
            asp_list = await asp.list(service_namespace=self.boto3_service_name, resource_id=self.resource_id)
            self._auto_scale_policies = asp_list
        return self._auto_scale_policies

    @scaling_policies.setter
    def scaling_policies(self, policy_list):
        class_type = self._get_service_class('app_scaling_policy')
        if isinstance(policy_list, list) and all(isinstance(policy, class_type) for policy in policy_list):
            self._auto_scale_policies = policy_list
        else:
            raise ValueError(f'{policy_list} != list<{class_type}>')


class BaseAutoScaleService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_service_field('scaling_policies', 'scaling_policy')

    async def load_scaling_policies(self):
        if not self.scaling_policies.loaded:
            await self.scaling_policies.list(self.name)


class BaseSecurityGroupService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_service_field('accessible_resources', 'security_group')
        self.create_service_field('security_groups', 'security_group')

    async def load_accessible_resources(self):
        if not self.security_groups.loaded:
            await self.security_groups.load()

        filter_list = [sg.id for sg in self.security_groups]
        if not filter_list:
            return self.accessible_resources

        self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
            Name='ip-permission.group-id',
            Values=filter_list
        )])

        return self.accessible_resources


class MetricService(BaseService):
    _available_metrics = False

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
        kwargs = {snake_to_camelcap(k): v for k, v in kwargs.items()}
        dimensions = self._stat_dimensions + kwargs.get('Dimensions', [])
        kwargs['Dimensions'] = dimensions

        if kwargs.get('ExtendedStatistics') is False and kwargs.get('Statistics') is False:
            LOGGER.warning('Neither ExtendedStatistics or Statistics was set. Defaulting to Statistics=[Average]')
            kwargs['Statistics'] = ['Average']

        metric_cls = self._get_service_class('metric')
        metrics = metric_cls.get_statistics(
            self._stat_name, metric_name, start_time, end_time, interval_as_seconds, **kwargs
        )
        return metrics

    @property
    async def available_metrics(self):
        if self._available_metrics is False:
            metrics = self._get_service_class('metric')
            metrics = await metrics.list(Namespace=self._stat_name, Dimensions=self._stat_dimensions)
            self._available_metrics = metrics
        return self._available_metrics

    @property
    async def metric_options(self):
        if self._available_metrics is False:
            metrics = self._get_service_class('metric')
            metrics = await metrics.list(Namespace=self._stat_name, Dimensions=self._stat_dimensions)
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


class SecurityGroup(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_security_groups
    """
    boto3_service_name = 'ec2'
    client_id = 'SecurityGroup'
    key_prefix = 'Group'
    _accessible_sg = False
    _boto3_describe_def = dict(
        client_call="describe_security_groups",
        call_params=dict(
            id=dict(name='GroupIds', type=list),
            name=dict(name='GroupNames', type=list),
        )
    )
    _response_alias = dict(user_id_group_pairs='security_group')


class LaunchConfiguration(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    """
    boto3_service_name = 'autoscaling'
    client_id = 'LaunchConfiguration'
    _boto3_describe_def = dict(
        call_params=dict(
            name=dict(name='LaunchConfigurationNames', type=list),
        )
    )

    async def _load(self):
        response = self.client.describe_launch_configurations(
            LaunchConfigurationNames=[self.name],
            MaxRecords=1
        )[f'{self.client_id}s']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

            user_data = getattr(self, 'user_data', "")
            self.user_data = base64.b64decode(self.user_data).decode("UTF-8") if user_data else user_data

        return self


class LoadBalancer(BaseSecurityGroupService, BaseService):
    boto3_service_name = 'elbv2'
    client_id = 'LoadBalancer'
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """

    @classmethod
    async def list(cls, **kwargs):
        """
        :param asg_name: Name of an AutoScaling Group
        :param kwargs:
        :return:
        """
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.describe_load_balancers, kwargs, f"{cls.client_id}s")
        return [cls(_loaded=True, **obj) for obj in response]


class LoadBalancerClassic(BaseSecurityGroupService, BaseService):
    boto3_service_name = 'elb'
    client_id = 'LoadBalancer'
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """

    async def _load(self):
        response = self.client.describe_load_balancers(
            LoadBalancerNames=[self.name]
        )['LoadBalancerDescriptions']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    async def list(cls, **kwargs):
        """
        :param kwargs:
        :return:
        """
        client = cls._client.get(cls.boto3_service_name)
        response = paginated_search(client.describe_load_balancers, kwargs, f"LoadBalancerDescriptions")
        return [cls(_loaded=True, **obj) for obj in response]


class EC2Instance(PaginatedBaseService):
    boto3_service_name = 'ec2'
    client_id = 'Instance'
    _boto3_describe_def = dict(
        call_params=dict(
            asg_name=dict(name='AutoScalingGroupName', type=str),
            name=dict(name='PolicyNames', type=list),
            type=dict(name='PolicyTypes', type=list)
        )
    )

    @classmethod
    async def _list(cls, filters=[], instance_ids=[], **kwargs) -> list:
        """
        boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances

        :param instance_ids: list<str>
        :param filters: list<dict> Available filter options available in the boto3 link above
        :return:
        """
        search_kwargs = dict(Filters=filters, InstanceIds=instance_ids)
        search_fnc = cls._client.get(cls.boto3_service_name).describe_instances
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


class ASG(PaginatedBaseService, BaseSecurityGroupService, BaseAutoScaleService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    """
    boto3_service_name = 'autoscaling'
    client_id = 'AutoScalingGroup'
    _boto3_describe_def = dict(
        call_params=dict(
            name=dict(name='AutoScalingGroupNames', type=list),
        )
    )

    async def load_accessible_resources(self):
        if self.accessible_resources.loaded:
            return self.accessible_resources

        launch_config = getattr(self, 'launch_configuration', None)
        if launch_config is None:
            return self.accessible_resources
        elif not launch_config.loaded:
            await launch_config.load()

        if not launch_config.security_groups.loaded:
            await launch_config.security_groups.load()

            filter_list = [sg.id for sg in launch_config.security_groups]
            if not filter_list:
                return self.accessible_resources

            self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
                Name='ip-permission.group-id',
                Values=filter_list
            )])

        return self.accessible_resources

    @property
    def security_groups(self) -> list:
        launch_config = getattr(self, 'launch_configuration', None)
        if launch_config:
            return launch_config.security_groups
        else:
            return []

    @classmethod
    async def get(cls, instance_id=None, **kwargs):
        """Hits the client to set the entirety of the object using the provided lookup field.
        :param instance_id: An EC2 instance ID
        :return:
        """
        if instance_id:
            client = cls._client.get(cls.boto3_service_name)
            response = client.describe_auto_scaling_instances(
                InstanceIds=[instance_id]
            )['AutoScalingInstances']
            if response:
                instance = response[0]
                kwargs['name'] = instance.get('AutoScalingGroupName')
            else:
                raise ValueError(f'{instance_id} not found or does not belong to an auto scaling group')
        obj = cls(**kwargs)
        return await obj.load()


class ECSTask(BaseService):
    boto3_service_name = 'ecs'
    client_id = 'task'

    async def _load(self):
        response = self.client.describe_tasks(
            cluster=self.cluster,
            tasks=[self.id]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    async def get(cls, id, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param id: string The task instance ID
        :return:
        """
        return await cls(id=id, cluster=cluster_name).load()

    @classmethod
    async def _list(cls, cluster_name, **kwargs):
        """
        For list of accepted kwarg values:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return await cls.list(describe_kwargs=dict(cluster=cluster_name), **kwargs)


class ECSService(BaseAppService, MetricService):
    boto3_service_name = 'ecs'
    client_id = 'service'
    _cluster = False

    async def _load(self):
        response = self.client.describe_services(
            cluster=self.cluster,
            services=[self.name]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @property
    async def cluster(self):
        if self._cluster is False:
            await self.load()
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
    async def get(cls, name, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param name: string The name of the service
        :return:
        """
        return await cls(name=name, cluster=cluster_name).load()

    @classmethod
    async def list(cls, cluster_name, **kwargs):
        """
        For list of accepted kwarg values:
        https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return await cls._list(describe_kwargs=dict(cluster=cluster_name), **kwargs)


class ECSInstance(BaseService):
    boto3_service_name = 'ecs'
    client_id = 'containerInstance'

    async def _load(self):
        response = self.client.describe_container_instances(
            cluster=self.cluster,
            containerInstances=[self.id]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    async def get(cls, id, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param id: string The Container instance ID
        :return:
        """
        return await cls(id=id, cluster=cluster_name).load()

    @classmethod
    async def list(cls, cluster_name, **kwargs):
        """
        For list of accepted kwarg values:
        https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html
            Both snake case as well as the exact key are accepted
        :param cluster_name:
        :param kwargs:
        :return:
        """
        kwargs['cluster'] = cluster_name
        return await cls._list(describe_kwargs=dict(cluster=cluster_name), **kwargs)


class ECSCluster(MetricService):
    boto3_service_name = 'ecs'
    client_id = 'cluster'
    _asg = False
    _instances = False
    _services = False

    async def _load(self):
        """
        boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_clusters
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
    async def asg(self):
        if self._asg is False:
            container_instance = await self.instances
            container_instance = container_instance[0]
            asg_obj = self._get_service_class('asg')
            self._asg = await asg_obj.get(instance_id=container_instance.ec2_instance_id)
        return self._asg

    @asg.setter
    def asg(self, asg):
        class_type = self._get_service_class('ecs_asg')
        if isinstance(asg, class_type):
            self._asg = asg
        else:
            raise ValueError(f'{asg} != {class_type}')

    @property
    async def instances(self):
        if self._instances is False:
            instance_obj = self._get_service_class('ecs_instance')
            self._instances = await instance_obj.list(self.name)
        return self._instances

    @instances.setter
    def instances(self, instance_list: list):
        class_type = self._get_service_class('ecs_instance')
        if isinstance(instance_list, list) and all(isinstance(instance, class_type) for instance in instance_list):
            self._instances = instance_list
        else:
            raise ValueError(f'{instance_list} != list<{class_type}>')

    @property
    async def services(self):
        if self._services is False:
            instance_obj = self._get_service_class('ecs_service')
            self._services = await instance_obj.list(self.name)
        return self._services

    @services.setter
    def services(self, services_list: list):
        class_type = self._get_service_class('ecs_service')
        if isinstance(services_list, list) and all(isinstance(svc, class_type) for svc in services_list):
            self._services = services_list
        else:
            raise ValueError(f'{services_list} != list<{class_type}>')

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='ClusterName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ECS'

    @classmethod
    async def get(cls, name, options=['ATTACHMENTS', 'STATISTICS', 'SETTINGS']):
        """
        :param name:
        :param options: list<`ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'>
        :return:
        """
        return await cls(name=name, _options=options).load()
