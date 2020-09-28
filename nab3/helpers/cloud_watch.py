import asyncio
from datetime import datetime as dt, timedelta

from double_click.markdown import generate_md_bullet_str, generate_md_table_str


def md_statistics_summary(metric_obj_list: list, include_table: bool = True) -> str:
    """Creates a markdown summary based on the provided get_statistics list response

    :param metric_obj_list:
    :param metric_name:
    :param include_table: Include an md table containing the datapoints used to generate the summary.
        Columns: Time Unit Average Maximum
    :return:
    """
    metric_name = metric_obj_list[0].name if metric_obj_list else ""
    md_output = f"### {metric_name}\n"
    if len(metric_obj_list) == 0:
        return md_output

    metric_attrs = metric_obj_list[0].__dict__.keys()
    # Remove irrelevant keys
    stats = [key for key in metric_attrs if key not in ['name', 'key_prefix', '_loaded', 'timestamp', 'unit']]
    headers = ['Time', 'Unit'] + [stat.title() for stat in stats]
    rows = []

    for data_point in metric_obj_list:
        rows.append([data_point.timestamp, data_point.unit] + [data_point.__dict__.get(stat) for stat in stats])
    rows.sort(key=lambda x: x[1])

    # Create a bulleted synopsis of each stat type in stats
    for stat in stats:
        md_output += f"#### {stat.title()}"
        agg_data = [data_point.__dict__.get(stat) for data_point in metric_obj_list]
        min_stat = min(agg_data)
        max_stat = max(agg_data)
        agg_stat = sum(agg_data)/len(rows)
        md_output += generate_md_bullet_str([
            f'Aggregate {stat.title()}: {agg_stat}',
            f'Minimum {stat.title()}: {min_stat}',
            f'Max {stat.title()}: {max_stat}'
        ])

    return f"{md_output}\n{generate_md_table_str(rows, headers)}" if include_table else md_output


async def md_alarms(scalable_object, start_date=dt.now()-timedelta(days=30), end_date=dt.now()) -> str:
    async def _asp_summary(scaling_policy):
        asp_alarms = scaling_policy.get_alarms(start_date=start_date, end_date=end_date, item_type='Action')
        asp_rows = [[scaling_policy.name, alarm.name, alarm.timestamp] for alarm in asp_alarms]
        return dict(policy_summary=f'{scaling_policy.name} - {len(asp_alarms)}', rows=asp_rows)

    md_output = ''

    if len(scalable_object.scaling_policies) == 0:
        return md_output

    md_output += '\n### Policies:\n'
    policy_summary = []
    headers = ['Policy', 'Alarm', 'Time']
    rows = []

    scaling_policy_summaries = await asyncio.gather(*[_asp_summary(asp) for asp in scalable_object.scaling_policies])
    for asp in scaling_policy_summaries:
        policy_summary.append(asp['policy_summary'])
        rows += asp['rows']

    if len(rows) == 0:
        return ''

    rows.sort(reverse=True, key=lambda x: x[2])
    return f"{md_output}{generate_md_bullet_str(policy_summary)}{generate_md_table_str(row_list=rows, headers=headers)}"


async def set_service_stats(service_obj,
                            stat_list: list = None,
                            start_date=dt.now()-timedelta(days=30),
                            end_date=dt.now(),
                            interval_as_seconds=1800):  # 30 minutes
    """Retrieves all statistics passed in stat_list for the service_obj.

    service_obj.stats = [dict(metric=str, stats=Metric())]

    :param service_obj:
    :param stat_list:
    :param start_date:
    :param end_date:
    :param interval_as_seconds:
    :return: service_obj
    """
    async def _stat(metric):
        return service_obj.get_statistics(metric_name=metric,
                                          statistics=['Average', 'Maximum'],
                                          start_time=start_date,
                                          end_time=end_date,
                                          interval_as_seconds=interval_as_seconds)  # 30 minutes

    stat_list = stat_list if stat_list else ['CPUUtilization', 'MemoryUtilization']
    service_obj.stats_list = await asyncio.gather(*[_stat(metric) for metric in stat_list])
    return service_obj


async def set_n_service_stats(service_list,
                              stat_list: list = None,
                              start_date=dt.now()-timedelta(days=30),
                              end_date=dt.now(),
                              interval_as_seconds=1800):  # 30 minutes
    """Retrieves all statistics passed in stat_list for each of the provided services in service_list.

    For each in service_list: service_obj.stats = [dict(metric=str, stats=Metric())]

    :param service_list:
    :param stat_list:
    :param start_date:
    :param end_date:
    :param interval_as_seconds:
    :return: service_list
    """
    return await asyncio.gather(*[
        set_service_stats(service_obj, stat_list, start_date, end_date, interval_as_seconds)
        for service_obj in service_list
    ])

