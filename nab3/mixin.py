import logging
from datetime import datetime as dt, timedelta

from nab3.utils import snake_to_camelcap

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

        self.scaling_policies = await self.scaling_policies.list(service_namespace=self.boto3_service_name,
                                                                 resource_id=self.resource_id)
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