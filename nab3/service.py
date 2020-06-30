from nab3.base import BaseService


class SecurityGroup(BaseService):
    boto3_service_name = 'ec2'
    client_name = 'SecurityGroup'
    key_prefix = 'Group'
    _service_list_map = dict(user_id_group_pairs='security_group')

    def load(self):
        group_id = getattr(self, 'id', None)
        group_name = getattr(self, 'name', None)
        if not group_id and not group_name:
            raise AttributeError('id or name must be set for load to be called')

        group_names = [group_name] if group_name else []
        group_ids = [group_id] if group_id else []
        security_groups = self.client.get(self.boto3_service_name).describe_security_groups(
            GroupIds=group_ids,
            GroupNames=group_names
        )['SecurityGroups']
        if security_groups:
            for k, v in security_groups[0].items():
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
    client_name = 'LaunchConfiguration'

    def load(self):
        client = self.client.get(self.boto3_service_name)
        launch_config = client.describe_launch_configurations(
            LaunchConfigurationNames=[self.name],
            MaxRecords=1
        )['LaunchConfigurations']
        if launch_config:
            for k, v in launch_config[0].items():
                self._set_attr(k, v)

        return self


class LoadBalancer(BaseService):
    boto3_service_name = 'elbv2'
    client_name = 'LoadBalancer'

    def load(self):
        pass


class ASG(BaseService):
    boto3_service_name = 'autoscaling'
    client_name = 'AutoScalingGroup'

    def load(self):
        client = self.client.get(self.boto3_service_name)
        launch_config = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.name]
        )[f'{self.client_name}s']
        if launch_config:
            for k, v in launch_config[0].items():
                self._set_attr(k, v)

        return self
