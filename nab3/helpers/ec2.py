from double_click.markdown import generate_md_table_str
from tqdm import tqdm


def md_security_group_table(sg_list: list, id_filter: list = []):
    headers = ['Name', 'Rule Type', 'Protocol', 'From', 'To']
    rows = []
    sg_list = sg_list if len(sg_list) < 5 else tqdm(sg_list)
    for sg in sg_list:
        sg.load()
        for ip_permissions in [dict(rule='Ingress', permissions=sg.ip_permissions),
                               dict(rule='Egress', permissions=sg.ip_permissions_egress)]:
            for ip_perm in ip_permissions['permissions']:
                for user_group in ip_perm.get('user_id_group_pairs', []):
                    if not id_filter or user_group.id in id_filter:
                        if user_group.id == sg.id:
                            name = f'Internal Rule - {sg.name}'
                        else:
                            user_group.load()
                            name = user_group.name
                    else:
                        continue

                    rows.append([
                        name, ip_permissions['rule'],
                        ip_perm.get('from_port', 'None'), ip_perm.get('from_port', 'None'),
                        ip_perm["ip_protocol"]
                    ])
    rows.sort(reverse=True, key=lambda x: x[0])
    return generate_md_table_str(row_list=rows, headers=headers)


def md_autoscale_sgs(asg_object):
    asg_object.load()
    security_groups = [sg for sg in asg_object.security_groups if sg.name != 'unix-admin']
    sg_table = md_security_group_table(security_groups)
    sg_names = [sg.id for sg in security_groups]
    resource_table = md_security_group_table(asg_object.accessible_resources, sg_names)
    return f"Security Groups\n{sg_table}\nAccessible Resources\n{resource_table}"


def md_autoscale_ips(asg_object):
    headers = ['Instance ID', 'IP', 'State']
    rows = []
    for instance in asg_object.instances:
        instance.load()
        rows.append([instance.id, instance.private_ip_address, instance.state['name']])

    return {generate_md_table_str(row_list=rows, headers=headers)}

