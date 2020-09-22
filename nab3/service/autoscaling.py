import base64
import logging

from nab3.mixin import AutoScaleMixin, MetricMixin, SecurityGroupMixin
from nab3.base import PaginatedBaseService

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class AutoScalePolicy(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_policies
    """
    boto3_client_name = 'autoscaling'
    key_prefix = 'Policy'
    _boto3_describe_def = dict(
        client_call='describe_policies',
        call_params=dict(
            asg_name=dict(name='AutoScalingGroupName', type=str),
            name=dict(name='PolicyNames', type=list),
            type=dict(name='PolicyTypes', type=list)
        ),
        response_key='ScalingPolicies'
    )

    def get_alarms(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        """
        alarms = []
        alarm_obj = self._get_service_class('alarm')

        for alarm in self.alarms:
            alarms += alarm_obj.get_history(name=alarm.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alarms


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
    boto3_client_name = 'application-autoscaling'
    key_prefix = 'Policy'
    _boto3_describe_def = dict(
        client_call='describe_scaling_policies',
        call_params=dict(
            scalable_dimension=dict(name='ScalableDimension', type=str),
            service_namespace=dict(name='ServiceNamespace', type=str),
            name=dict(name='PolicyNames', type=list),
            resource_id=dict(name='ResourceId', type=str)
        ),
        response_key='ScalingPolicies'
    )

    def get_alarms(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True):
        """
        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        """
        alarms = []
        alarm_obj = self._get_service_class('alarm')
        for alarm in self.alarms:
            alarms += alarm_obj.get_history(name=alarm.name, start_date=start_date, end_date=end_date,
                                            item_type=item_type, alarm_types=alarm_types, sort_descending=sort_desc)

        return alarms


class LaunchConfiguration(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    """
    boto3_client_name = 'autoscaling'
    key_prefix = 'LaunchConfiguration'
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


class ASG(SecurityGroupMixin, AutoScaleMixin, MetricMixin, PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_auto_scaling_groups
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    """
    boto3_client_name = 'autoscaling'
    key_prefix = 'AutoScalingGroup'
    _boto3_describe_def = dict(
        call_params=dict(
            name=dict(name='AutoScalingGroupNames', type=list),
        )
    )

    async def load_security_groups(self):
        """Retrieves the instances related security groups.

        stored as the instance attribute `obj.security_groups`

        :return: list<SecurityGroup>
        """
        if self.security_groups.loaded:
            return self.security_groups

        launch_config = getattr(self, 'launch_configuration', None)
        if launch_config is None:
            return self.security_groups
        elif not launch_config.loaded:
            await launch_config.load()

        await launch_config.fetch('security_groups')
        self.security_groups = launch_config.security_groups
        return self.security_groups

    @classmethod
    async def get(cls, instance_id=None, with_related=[], **kwargs):
        """Hits the client to set the entirety of the object using the provided lookup field.
        :param instance_id: An EC2 instance ID
        :param with_related: list of related AWS resources to return
        :return:
        """
        if instance_id:
            client = cls._client.get(cls.boto3_client_name)
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

    @property
    def _stat_dimensions(self) -> list:
        return [dict(Name='AutoScalingGroupName', Value=self.name)]

    @property
    def _stat_name(self) -> str:
        return 'AWS/EC2'
