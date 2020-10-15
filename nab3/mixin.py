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

    async def load_scaling_policies(self, force=False):
        if self.scaling_policies.is_loaded() and not force:
            return self.scaling_policies

        self.scaling_policies = await self.scaling_policies.list(service_namespace=self.boto3_client_name,
                                                                 resource_id=self.resource_id)
        return self.scaling_policies


class AutoScaleMixin:

    def __init__(self, **kwargs):
        self.create_service_field('scaling_policies', 'scaling_policy')
        super().__init__(**kwargs)

    async def load_scaling_policies(self, force=False):
        if self.scaling_policies.is_loaded() and not force:
            return self.scaling_policies

        scaling_policies = await self.scaling_policies.list(asg_name=self.name)
        self.scaling_policies = scaling_policies
        return self.scaling_policies


class SecurityGroupMixin:
    def __init__(self, **kwargs):
        self.create_service_field('accessible_resources', 'security_group')
        self.create_service_field('security_groups', 'security_group')
        super().__init__(**kwargs)

    async def load_accessible_resources(self, force=False):
        if self.accessible_resources.is_loaded() and not force:
            return self.accessible_resources

        await self.fetch('security_groups', force=force)

        filter_list = [sg.id for sg in self.security_groups]
        if not filter_list:
            return self.accessible_resources

        self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
            Name='ip-permission.group-id',
            Values=filter_list
        )])

        return self.accessible_resources


class PricingMixin:
    def __init__(self, **kwargs):
        self.create_service_field('pricing', 'pricing')
        super().__init__(**kwargs)

    async def load_pricing(self, force=False):
        if self.pricing.is_loaded() and not force:
            return self.pricing

        pricing = await self.pricing.list(**self._pricing_params)
        if len(pricing) > 0:
            self.pricing = pricing[0]

        return self.pricing

    async def get_on_demand_hourly(self, currency='usd'):
        if not self.pricing.is_loaded():
            await self.fetch('pricing')

        return self.pricing.get_on_demand_hourly(currency)

    async def get_on_demand_monthly(self, currency='usd'):
        if not self.pricing.is_loaded():
            await self.fetch('pricing')

        return self.pricing.get_on_demand_monthly(currency)

    @property
    def _pricing_params(self) -> dict:
        # returns dict(service_code=str, filters=list(dict(Field=str, Value=str, Type=str)))
        raise NotImplementedError


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
