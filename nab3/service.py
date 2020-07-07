from itertools import chain

from nab3.base import BaseService
from nab3.utils import paginated_search


class SecurityGroup(BaseService):
    boto3_service_name = 'ec2'
    client_id = 'SecurityGroup'
    key_prefix = 'Group'
    _service_list_map = dict(user_id_group_pairs='security_group')

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


class ASG(BaseService):
    boto3_service_name = 'autoscaling'
    client_id = 'AutoScalingGroup'

    @property
    def scaling_policies(self):
        asp_list = getattr(self, '_auto_scale_policies', None)
        if asp_list:
            return asp_list

        asp = self._get_service_class('scaling_policy')
        asp_list = asp.list(asg_name=self.name)
        self._auto_scale_policies = asp_list
        return self._auto_scale_policies

    def _load(self):
        response = self.client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.name]
        )[f'{self.client_id}s']
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self


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
    def list(cls, cluster_name):
        search_kwargs = dict(cluster=cluster_name)
        search_fnc = cls._client.get(cls.boto3_service_name).describe_tasks
        results = paginated_search(search_fnc, search_kwargs, 'tasks')
        return [cls(_loaded=True, **result) for result in results]


class ECSService(BaseService):
    boto3_service_name = 'ecs'
    client_id = 'service'

    def _load(self):
        response = self.client.describe_services(
            cluster=self.cluster,
            services=[self.name]
        ).get(f'{self.client_id}s')
        if response:
            for k, v in response[0].items():
                self._set_attr(k, v)

        return self

    @classmethod
    def get(cls, name, cluster_name):
        """
        :param cluster_name: string Name of the ECS Cluster the instance belongs to
        :param name: string The name of the service
        :return:
        """
        return cls(name=name, cluster=cluster_name).load()

    @classmethod
    def list(cls, cluster_name):
        search_kwargs = dict(cluster=cluster_name)
        search_fnc = cls._client.get(cls.boto3_service_name).list_services
        results = paginated_search(search_fnc, search_kwargs, 'serviceArns')
        return [cls(name=result.split('/')[-1], cluster=cluster_name).load() for result in results]


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
    def list(cls, cluster_name):
        search_kwargs = dict(cluster=cluster_name)
        search_fnc = cls._client.get(cls.boto3_service_name).list_container_instances
        results = paginated_search(search_fnc, search_kwargs, 'containerInstanceArns')
        return [cls(id=result.split('/')[-1], cluster=cluster_name).load() for result in results]


class ECSCluster(BaseService):
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

    @classmethod
    def get(cls, name, options=['STATISTICS']):
        """Hits the client to set the entirety of the object using the provided lookup field.

        Default filter field is normally name

        :param name:
        :param options: list<`ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS'>
        :return:
        """
        return cls(name=name, _options=options).load()
