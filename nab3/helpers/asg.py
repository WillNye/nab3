from datetime import datetime as dt, timedelta

from double_click import echo
from double_click.markdown import generate_md_bullet_str, generate_md_table_str
from tqdm import tqdm


def display_asg_sgs(asg_object):
    headers = ['Name', 'Rule Type', 'Protocol', 'From', 'To']
    rows = []

    l_config = asg_object.launch_configuration.load()
    for sg in tqdm(l_config.security_groups):
        sg.load()
        for ip_perm in sg.ip_permissions:
            for user_group in ip_perm.get('user_id_group_pairs', []):
                user_group.load()
                rows.append([
                    user_group.name, 'Ingress', ip_perm["from_port"], ip_perm["to_port"], ip_perm["ip_protocol"]
                ])

        for ip_perm in sg.ip_permissions_egress:
            for user_group in ip_perm.get('user_id_group_pairs', []):
                user_group.load()
                rows.append([
                    user_group.name, 'Egress', ip_perm["from_port"], ip_perm["to_port"], ip_perm["ip_protocol"]
                ])

    echo(f"# {asg_object.name} Security Groups\n{generate_md_table_str(row_list=rows, headers=headers)}")


def display_asg_alerts(asg_object, start_date=dt.now()-timedelta(days=30), end_date=dt.now()):
    md_output = f'# {asg_object.name}\n## Policies:\n'
    policy_summary = []
    headers = ['Policy', 'Alarm', 'Time']
    rows = []
    for asp in tqdm(asg_object.scaling_policies):
        alerts = asp.get_alerts(start_date=start_date, end_date=end_date, item_type='Action')
        policy_summary.append(f'{asp.name} - {len(alerts)}')
        rows += [[asp.name, alert.name, alert.timestamp] for alert in alerts]

    md_output += f"{generate_md_bullet_str(policy_summary)}{generate_md_table_str(row_list=rows, headers=headers)}"
    echo(md_output)


def display_asg_ips(asg_object):
    headers = ['Instance ID', 'IP', 'State']
    rows = []
    for instance in asg_object.instances:
        instance.load()
        rows.append([instance.id, instance.private_ip_address, instance.state['name']])

    echo(f"# {asg_object.name}\n{generate_md_table_str(row_list=rows, headers=headers)}")

