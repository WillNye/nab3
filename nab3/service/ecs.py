import logging

from nab3.mixin import AppAutoScaleMixin, AutoScaleMixin, MetricMixin
from nab3.base import BaseService

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class ECSTask(BaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_tasks
    """
    boto3_client_name = 'ecs'
    key_prefix = 'task'
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
    boto3_client_name = 'ecs'
    key_prefix = 'service'
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
        return f"{self.key_prefix}/{self.cluster}/{self.name}"

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
    boto3_client_name = 'ecs'
    key_prefix = 'containerInstance'
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
    boto3_client_name = 'ecs'
    key_prefix = 'cluster'
    _boto3_describe_def = dict(
        call_params=dict(
            name=dict(name='clusters', type=list),  # list<str>
            include=dict(name='include', type=list),  # list<str> ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'
        )
    )

    def __init__(self, **kwargs):
        self.create_service_field('asg', 'asg')
        self.create_service_field('instances', 'ecs_instance')
        self.create_service_field('services', 'ecs_service')
        super(self._get_service_class('ecs_cluster'), self).__init__(**kwargs)

    async def load_asg(self):
        """Retrieves the instances asg.

        stored as the instance attribute `obj.asg`

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

        :return: ASG
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
        """Retrieves the cluster's instances.

        stored as the instance attribute `obj.instances`

        :return: list<instances>
        """
        if self.instances.loaded:
            return self.instances
        self.instances = await self.instances.list(cluster=self.name)
        return self.instances

    async def load_services(self):
        """Retrieves the cluster's services.

        stored as the instance attribute `obj.services`

        :return: list<services>
        """
        if self.services.loaded:
            return self.services

        services = []
        for service in await self.services.list(cluster=self.name):
            service.cluster = self.name
            services.append(service)
        self.services = services

        return self.services

    async def load_scaling_policies(self):
        """Retrieves the cluster's scaling policies.

        stored as the instance attribute `obj.scaling_policies`

        :return: list<scaling_policies>
        """
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