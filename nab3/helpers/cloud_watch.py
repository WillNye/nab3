from datetime import datetime as dt, timedelta

from double_click.markdown import generate_md_bullet_str, generate_md_table_str


def md_statistics_summary(metric_obj_list: list, metric_name: str) -> str:
    """Creates a markdown summary based on the provided get_statistics list response

    :param metric_obj_list:
    :param metric_name:
    :return:
    """
    md_output = f"### {metric_name}\n"
    if len(metric_obj_list) == 0:
        return md_output

    metric_attrs = metric_obj_list[0].__dict__.keys()
    # Remove irrelevant keys
    stats = [key for key in metric_attrs if key not in ['key_prefix', '_loaded', 'timestamp', 'unit']]
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

    return f"{md_output}\n#### {metric_name} Table:\n{generate_md_table_str(rows, headers)}"


def md_alarms(scalable_object, start_date=dt.now()-timedelta(days=30), end_date=dt.now()) -> str:
    md_output = ''

    if len(scalable_object.scaling_policies) == 0:
        return md_output

    md_output += '\n### Policies:\n'
    policy_summary = []
    headers = ['Policy', 'Alarm', 'Time']
    rows = []

    for asp in scalable_object.scaling_policies:
        alarms = asp.get_alarms(start_date=start_date, end_date=end_date, item_type='Action')
        policy_summary.append(f'{asp.name} - {len(alarms)}')
        rows += [[asp.name, alarm.name, alarm.timestamp] for alarm in alarms]

    if len(rows) == 0:
        return ''

    rows.sort(reverse=True, key=lambda x: x[2])
    return f"{md_output}{generate_md_bullet_str(policy_summary)}{generate_md_table_str(row_list=rows, headers=headers)}"
