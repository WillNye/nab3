from datetime import datetime as dt, timedelta

from double_click import echo
from double_click.markdown import generate_md_bullet_str, generate_md_table_str
from tqdm import tqdm


def generated_md_alerts(scalable_object, start_date=dt.now()-timedelta(days=30), end_date=dt.now(), include_name=True):
    scalable_object.load()
    md_output = f'# {scalable_object.name}' if include_name else ''

    if len(scalable_object.scaling_policies) == 0:
        return md_output

    md_output += '\n## Policies:\n'
    policy_summary = []
    headers = ['Policy', 'Alarm', 'Time']
    rows = []

    for asp in tqdm(scalable_object.scaling_policies):
        alerts = asp.get_alerts(start_date=start_date, end_date=end_date, item_type='Action')
        policy_summary.append(f'{asp.name} - {len(alerts)}')
        rows += [[asp.name, alert.name, alert.timestamp] for alert in alerts]

    return f"{md_output}{generate_md_bullet_str(policy_summary)}{generate_md_table_str(row_list=rows, headers=headers)}"


def display_alerts(scalable_object, start_date=dt.now()-timedelta(days=30), end_date=dt.now()):
    echo(generated_md_alerts(scalable_object, start_date, end_date))
