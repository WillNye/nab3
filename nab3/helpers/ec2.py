from double_click import echo
from double_click.markdown import generate_md_table_str
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

    echo(f"## {asg_object.name} Security Groups\n{generate_md_table_str(row_list=rows, headers=headers)}")


def display_asg_ips(asg_object):
    headers = ['Instance ID', 'IP', 'State']
    rows = []
    for instance in asg_object.instances:
        instance.load()
        rows.append([instance.id, instance.private_ip_address, instance.state['name']])

    echo(f"# {asg_object.name}\n{generate_md_table_str(row_list=rows, headers=headers)}")

