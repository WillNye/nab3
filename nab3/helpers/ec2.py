from double_click.markdown import generate_md_bullet_str, generate_md_table_str
from tqdm import tqdm


def md_security_group_table(sg_list: list, id_filter: list = []):
    headers = ['Name', 'SG/CIDR', 'Rule Type', 'Protocol', 'From', 'To']
    rows = []
    sg_list = sg_list if len(sg_list) < 5 else tqdm(sg_list)
    for sg in sg_list:
        for ip_permissions in [dict(rule='Ingress', permissions=sg.ip_permissions),
                               dict(rule='Egress', permissions=sg.ip_permissions_egress)]:
            for ip_perm in ip_permissions['permissions']:
                rule_list = [ip_permissions['rule'],
                             ip_perm.get('from_port', 'None'),
                             ip_perm.get('from_port', 'None'),
                             ip_perm["ip_protocol"]]
                for user_group in ip_perm.get('user_id_group_pairs', []):
                    if not id_filter or user_group.id in id_filter:
                        if user_group.id == sg.id:
                            name = f'Internal Rule - {sg.name}'
                        else:
                            name = user_group.name
                    else:
                        continue
                    rows.append([name, user_group.id] + rule_list)

                for ip_range in ip_perm.get('ip_ranges', []):
                    if ip_range.get('cidr_ip') == '0.0.0.0/0':
                        continue
                    rows.append([ip_range.get('description', "N/A"), f"IP {ip_range.get('cidr_ip')}"] + rule_list)

                for ip_range in ip_perm.get('ipv6_ranges', []):
                    if ip_range.get('cidr_ipv6') == '0.0.0.0/0':
                        continue
                    rows.append([ip_range.get('description', "N/A"), f"IPV6 {ip_range.get('cidr_ipv6')}"] + rule_list)

    if rows:
        rows.sort(reverse=True, key=lambda x: x[0])
        return generate_md_table_str(row_list=rows, headers=headers)


def md_autoscale_sgs(asg_object):
    security_groups = [sg for sg in asg_object.security_groups if sg.name != 'unix-admin']
    if not security_groups:
        return ""

    sg_names = [sg.id for sg in security_groups]
    md_output = f"### Security Groups:\n{generate_md_bullet_str(sg_names)}\n"
    sg_table = md_security_group_table(security_groups)
    resource_table = md_security_group_table(asg_object.accessible_resources, sg_names)

    if sg_table:
        md_output += f"#### Rule Summary\n{sg_table}\n"
    if resource_table:
        md_output += f"Accessible Resources\n{resource_table}\n"

    return md_output


def md_autoscale_ips(asg_object):
    headers = ['Instance ID', 'IP', 'State']
    rows = []
    instances = asg_object.instances
    for instance in instances:
        rows.append([instance.id, instance.private_ip_address, instance.state['name']])

    return generate_md_table_str(row_list=rows, headers=headers)

