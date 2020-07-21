import base64
import logging
from itertools import chain
from datetime import datetime as dt, timedelta

from nab3.base import BaseService, PaginatedBaseService
from nab3.utils import paginated_search, snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class AppAutoScaleMixin:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_service_field('scaling_policies', 'app_scaling_policy')

    @property
    def resource_id(self):
        raise NotImplementedError

    async def load_scaling_policies(self):
        if self.scaling_policies.loaded:
            return self.scaling_policies

        asp_list = await self.scaling_policies.list(resource_id=self.resource_id)
        self.scaling_policies = asp_list
        return self.scaling_policies


class AutoScaleMixin:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_service_field('scaling_policies', 'scaling_policy')

    async def load_scaling_policies(self):
        if not self.scaling_policies.loaded:
            self.scaling_policies = await self.scaling_policies.list(asg_name=self.name)


class SecurityGroupMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_service_field('accessible_resources', 'security_group')
        self.create_service_field('security_groups', 'security_group')

    async def load_accessible_resources(self):
        if self.accessible_resources.loaded:
            return self.accessible_resources

        if not self.security_groups.loaded:
            await self.fetch('security_groups')

        filter_list = [sg.id for sg in self.security_groups]
        if not filter_list:
            return self.accessible_resources

        self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
            Name='ip-permission.group-id',
            Values=filter_list
        )])

        return self.accessible_resources


class MetricMixin:
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

    async def get_available_metrics(self):
        if self._available_metrics is False:
            metrics = self._get_service_class('metric')
            metrics = await metrics.list(Namespace=self._stat_name, Dimensions=self._stat_dimensions)
            self._available_metrics = metrics
        return self._available_metrics

    async def get_metric_options(self):
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


class Alarm(PaginatedBaseService):
    boto3_service_name = 'cloudwatch'
    client_id = 'Alarm'

    @classmethod
    def get_history(cls, start_date, end_date, name=None, item_type=None, alarm_types=[], sort_descending=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param name: AlarmName='string'
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_descending: bool -> ScanBy='TimestampDescending TimestampAscending'
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


class Metric(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.list_metrics
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics
    docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#dimension-combinations
    """
    boto3_service_name = 'cloudwatch'
    client_id = 'Metric'
    _boto3_describe_def = dict(
        client_call="list_metrics",
        call_params=dict(
            dimensions=dict(name='Dimensions', type=list),  # list<dict(Name=str, Value=str)>
            name=dict(name='MetricName', type=str),
            namespace=dict(name='Namespace', type=str),
        )
    )

    @classmethod
    def get_statistics(cls, namespace, metric_name, start_time, end_time, interval_as_seconds, **kwargs):
        """
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
                'SampleCount Average Sum Minimum Maximum',
            ],
            ExtendedStatistics=[
                'string',
            ]) - Statistics or ExtendedStatistics must be set ,
            Unit='Seconds Microseconds Milliseconds Bytes Kilobytes Megabytes 
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


class AutoScalePolicy(PaginatedBaseService):
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
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        """
        alerts = []
        alert_obj = self._get_service_class('alarm')

        for alert in self.alarms:
            alerts += alert_obj.get_history(name=alert.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alerts


class AppAutoScalePolicy(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/application-autoscaling.html#ApplicationAutoScaling.Client.describe_scaling_policies
    
    Scalable Dimension options:
        ecs:service:DesiredCount
        ec2:spot-fleet-request:TargetCapacity
        elasticmapreduce:instancegroup:InstanceCount
        appstream:fleet:DesiredCapacity
        dynamodb:table:ReadCapacityUnits
        dynamodb:table:WriteCapacityUnits
        dynamodb:index:ReadCapacityUnits
        dynamodb:index:WriteCapacityUnits
        rds:cluster:ReadReplicaCount
        sagemaker:variant:DesiredInstanceCount
        custom-resource:ResourceType:Property c
        omprehend:document-classifier-endpoint:DesiredInferenceUnits
        lambda:function:ProvisionedConcurrency
        cassandra:table:ReadCapacityUnits
        cassandra:table:WriteCapacityUnits
    """
    boto3_service_name = 'application-autoscaling'
    client_id = 'Policy'
    _boto3_describe_def = dict(
        client_call='describe_scaling_policies',
        call_params=dict(
            scalable_dimension=dict(name='ScalableDimension', type=str),
            name=dict(name='PolicyNames', type=list),
            resource_id=dict(name='ResourceId', type=str)
        ),
        response_key='ScalingPolicies'
    )

    def get_alerts(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        """
        alerts = []
        alert_obj = self._get_service_class('alarm')
        for alert in self.alarms:
            alerts += alert_obj.get_history(name=alert.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alerts


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


class LaunchConfiguration(PaginatedBaseService):
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
    _user_data = None

    @property
    def user_data(self):
        return self._user_data

    @user_data.setter
    def user_data(self, user_data=None):
        self._user_data = base64.b64decode(user_data).decode("UTF-8") if user_data else user_data


class LoadBalancer(SecurityGroupMixin, BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """
    boto3_service_name = 'elbv2'
    client_id = 'LoadBalancer'
    _boto3_describe_def = dict(
        call_params=dict(
            arn=dict(name='LoadBalancerArns', type=list),  # list<str>
            name=dict(name='Names', type=list),  # list<str>
        )
    )


class LoadBalancerClassic(SecurityGroupMixin, BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    """
    boto3_service_name = 'elb'
    client_id = 'LoadBalancer'
    _boto3_describe_def = dict(
        client_call='describe_load_balancers',
        call_params=dict(
            name=dict(name='LoadBalancerNames', type=list)  # list<str>
        ),
        response_key='LoadBalancerDescriptions'
    )


class EC2Instance(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    """
    boto3_service_name = 'ec2'
    client_id = 'Instance'
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


class ASG(SecurityGroupMixin, AutoScaleMixin, PaginatedBaseService):
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

    async def load_security_groups(self):
        if self.security_groups.loaded:
            return self.security_groups

        launch_config = getattr(self, 'launch_configuration', None)
        if launch_config is None:
            return self.security_groups
        elif not launch_config.loaded:
            await launch_config.load()

        self.security_groups = await launch_config.fetch('security_groups')
        return self.security_groups

    @classmethod
    async def get(cls, instance_id=None, with_related=[], **kwargs):
        """Hits the client to set the entirety of the object using the provided lookup field.
        :param instance_id: An EC2 instance ID
        :param with_related: list of related AWS resources to return
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
        await obj.load()
        if with_related:
            await obj.fetch(*with_related)
        return obj


class ECSTask(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_tasks
    """
    boto3_service_name = 'ecs'
    client_id = 'task'
    _boto3_describe_def = dict(
        client_call="list_metrics",
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            id=dict(name='tasks', type=list),  # list<str>
            include=dict(name='include', type=list),  # list<str>
        )
    )
    _boto3_list_def = dict(
        client_call="list_tasks",
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            container_instance=dict(name='containerInstance', type=str),
            family=dict(name='family', type=str),
            started_by=dict(name='startedBy', type=str),
            service_name=dict(name='serviceName', type=str),
            desired_status=dict(name='desiredStatus', type=str),
            launch_type=dict(name='launchType', type=str),
        )
    )


class ECSService(MetricMixin, AppAutoScaleMixin, BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_services
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services
    """
    boto3_service_name = 'ecs'
    client_id = 'service'
    _boto3_describe_def = dict(
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            name=dict(name='services', type=list),  # list<str>
            include=dict(name='include', type=list),  # list<str> e.g. TAGS
        )
    )
    _boto3_list_def = dict(
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            launch_type=dict(name='launchType', type=str),  # 'EC2'|'FARGATE'
            scheduling_strategy=dict(name='schedulingStrategy', type=str)  # 'REPLICA'|'DAEMON'
        )
    )

    def __init__(self, **kwargs):
        super(self._get_service_class('ecs_service'), self).__init__(**kwargs)
        cluster_arn = kwargs.get('cluster_arn', None)
        if cluster_arn:
            self.cluster = cluster_arn.split('/')[-1]
            delattr(self, 'cluster_arn')

    @property
    def resource_id(self):
        return f"{self.client_id}/{self.cluster}/{self.name}"

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='ClusterName', Value=self.cluster), dict(Name='ServiceName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ECS'


class ECSInstance(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_container_instances
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_container_instances

    For filter see docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html but...
        It appears to be client side so it's likely easier to use nab3.Filter

    Valid status options:
        ACTIVE
        DRAINING
        REGISTERING
        DEREGISTERING
        REGISTRATION_FAILED
    """
    boto3_service_name = 'ecs'
    client_id = 'containerInstance'
    _boto3_describe_def = dict(
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            id=dict(name='containerInstances', type=list),  # list<str>
            include=dict(name='include', type=list),  # list<str> e.g. TAGS
        )
    )
    _boto3_list_def = dict(
        call_params=dict(
            cluster=dict(name='cluster', type=str),
            filter=dict(name='filter', type=str),  # 'EC2'|'FARGATE'
            status=dict(name='status', type=str)
        )
    )


class ECSCluster(AutoScaleMixin, MetricMixin, BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_clusters
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_clusters
    """
    boto3_service_name = 'ecs'
    client_id = 'cluster'
    _boto3_describe_def = dict(
        call_params=dict(
            name=dict(name='clusters', type=list),  # list<str>
            include=dict(name='include', type=list),  # list<str> ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'
        )
    )

    def __init__(self, **kwargs):
        super(self._get_service_class('ecs_cluster'), self).__init__(**kwargs)
        self.create_service_field('asg', 'asg')
        self.create_service_field('instances', 'ecs_instance')
        self.create_service_field('services', 'ecs_service')

    async def load_asg(self):
        """

        if self.scaling_policies.loaded:
            return self.scaling_policies


        if not self.security_groups.loaded:
            await self.fetch('security_groups')

        filter_list = [sg.id for sg in self.security_groups]
        if not filter_list:
            return self.accessible_resources

        self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
            Name='ip-permission.group-id',
            Values=filter_list
        )])

        return self.accessible_resources

        :return:
        """
        if self.asg.loaded:
            return self.asg
        if not self.instances.loaded:
            await self.fetch('instances')

        container_instances = [instance for instance in self.instances]
        if len(container_instances) > 0:
            container_instance = container_instances[0]
            self.asg = await self.asg.get(instance_id=container_instance.ec2_instance_id)

        return self.asg

    async def load_instances(self):
        if self.instances.loaded:
            return self.instances
        self.instances = await self.instances.list(cluster=self.name)
        return self.instances

    async def load_services(self):
        if self.services.loaded:
            return self.services
        self.services = await self.services.list(cluster=self.name)
        return self.services

    async def load_scaling_policies(self):
        if self.scaling_policies.loaded:
            return self.scaling_policies
        if not self.asg.loaded:
            await self.fetch('asg')

        if self.asg:
            await self.asg.fetch('scaling_policies')
            self.scaling_policies = self.asg.scaling_policies
        return self.scaling_policies

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='ClusterName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/ECS'
