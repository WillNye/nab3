import logging

from nab3.base import PaginatedBaseService
from nab3.utils import paginated_search, snake_to_camelcap

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class Alarm(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.describe_alarm_history
    """
    boto3_client_name = 'cloudwatch'
    key_prefix = 'Alarm'

    @classmethod
    def get_history(cls, start_date, end_date, name=None, item_type=None, alarm_types=None, sort_descending=True):
        """ Retrieves the history for the specified alarm.
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

        search_fnc = cls._client.get(cls.boto3_client_name).describe_alarm_history
        results = paginated_search(search_fnc, search_kwargs, 'AlarmHistoryItems')
        return [cls(_loaded=True, **result) for result in results]


class Metric(PaginatedBaseService):
    """
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.list_metrics
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics
    docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#dimension-combinations
    """
    boto3_client_name = 'cloudwatch'
    key_prefix = 'Metric'
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

        client = cls._client.get(cls.boto3_client_name)
        response = client.get_metric_statistics(**search_kwargs)
        return [cls(name=metric_name, _loaded=True, **obj) for obj in response.get('Datapoints', [])]

    @classmethod
    def get(cls, **kwargs):
        raise NotImplementedError("get is not a supported operation for Metric")

    @classmethod
    def load(cls, **kwargs):
        raise NotImplementedError("load is not a supported operation for Metric")
