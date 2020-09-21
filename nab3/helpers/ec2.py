from double_click.markdown import generate_md_bullet_str, generate_md_table_str


def md_security_group_table(sg_list: list, id_filter: list = [], is_accessible_resources: bool = False):
    headers = ['Security Group', 'Rule Name', 'SG/CIDR', 'Rule Type', 'Protocol', 'From', 'To']
    rows = []
    for sg in sg_list:
        for ip_permissions in [dict(rule='Ingress', permissions=sg.ip_permissions),
                               dict(rule='Egress', permissions=sg.ip_permissions_egress)]:
            for ip_perm in ip_permissions['permissions']:
                rule_list = [ip_permissions['rule'],
                             ip_perm["ip_protocol"],
                             ip_perm.get('from_port', 'None'),
                             ip_perm.get('to_port', 'None')]
                for user_group in ip_perm.get('user_id_group_pairs', []):
                    sg_id = user_group.get('group_id')
                    if sg_id and (not id_filter or sg_id in id_filter):
                        if sg_id == sg.id:
                            name = f'Internal Rule - {sg.name}'
                        else:
                            if is_accessible_resources:
                                name = sg.name
                            else:
                                name = user_group.get("description", "N/A")
                    else:
                        continue
                    rows.append([sg.id, name, sg_id] + rule_list)

                if is_accessible_resources:
                    continue

                for ip_range in ip_perm.get('ip_ranges', []):
                    if ip_range.get('cidr_ip') == '0.0.0.0/0':
                        continue

                    rows.append(
                        [sg.id, ip_range.get("description", "N/A"), f"IP {ip_range.get('cidr_ip')}"] + rule_list
                    )

                for ip_range in ip_perm.get('ipv6_ranges', []):
                    if ip_range.get('cidr_ipv6') == '0.0.0.0/0' or (id_filter and sg.id not in id_filter):
                        continue

                    rows.append(
                        [sg.id, ip_range.get("description", "N/A"), f"IPV6 {ip_range.get('cidr_ipv6')}"] + rule_list
                    )

    if rows:
        if is_accessible_resources:
            rows.sort(key=lambda x: x[2])
        else:
            rows.sort(key=lambda x: x[0])
        return generate_md_table_str(row_list=rows, headers=headers)


def md_sg_summary(service_object):
    security_groups = [sg for sg in service_object.security_groups if sg.name != 'unix-admin']
    if not security_groups:
        return ""

    sg_str_list = [f'{sg.name} ({sg.id})' for sg in security_groups]
    md_output = f"### Security Groups:\n{generate_md_bullet_str(sg_str_list)}\n"
    sg_table = md_security_group_table(security_groups)
    resource_table = md_security_group_table(service_object.accessible_resources, [sg.id for sg in security_groups], True)

    if sg_table:
        md_output += f"#### Rule Summary\n{sg_table}\n"
    if resource_table:
        md_output += f"#### Accessible Resources\n{resource_table}\n"

    return md_output


def md_autoscale_ips(asg_object):
    headers = ['Instance ID', 'IP', 'State']
    rows = []
    instances = asg_object.instances
    for instance in instances:
        rows.append([instance.id, instance.private_ip_address, instance.state['name']])

    return generate_md_table_str(row_list=rows, headers=headers)

