import asyncio

from double_click.markdown import generate_md_bullet_str, generate_md_table_str

from nab3.helpers.cloud_watch import md_alarms


async def md_ecs_service_summary(ecs_service, display_alarms=True, display_events=True) -> str:
    """
    :param ecs_service: ECSService object
    :param display_alarms: bool Default(True) - Display service cloudwatch alarms for the last 30 days
    :param display_events: bool Default(True) - Display the 50 most recent events of the service
    :return:
    """
    task_def = ecs_service.task_definition.split("task-definition/")[-1]
    bullets = [
        f"Task Definition: {task_def}",
        f"Status: {ecs_service.status}",
        f"Desired Count: {ecs_service.desired_count}",
        f"Running Count: {ecs_service.running_count}",
        f"Pending Count: {ecs_service.pending_count}"
    ]
    md_output = f"# {ecs_service.name}\n{generate_md_bullet_str(bullets)}"
    if display_events:
        headers = ["Event", "Occurred At"]
        rows = [[event.get('message')[:50], event.get('created_at')] for event in ecs_service.events]
        rows.sort(reverse=True, key=lambda x: x[1])
        md_output += f"\n### Events{generate_md_table_str(rows, headers)}"

    if display_alarms:
        alarm_str = await md_alarms(ecs_service)
        md_output += alarm_str

    return md_output


async def md_ecs_cluster_summary(ecs_cluster, display_alarms=True, display_service_events=False) -> str:
    """
    :param ecs_cluster: ECSCluster object
    :param display_alarms: bool Default(True) - Display cloudwatch alarms for the last 30 days
    :param display_service_events: bool Default(True) - Display the 50 most recent events of each service
    :return:
    """
    bullets = [
        f"Status: {ecs_cluster.status}",
        f"Instance Count: {ecs_cluster.registered_container_instances_count}"
    ] + [f"{stat.get('name')}: {stat.get('value')}" for stat in ecs_cluster.statistics if int(stat.get('value')) > 0]

    md_output = f"# {ecs_cluster.name}\n{generate_md_bullet_str(bullets)}"

    if display_alarms:
        alarm_str = await md_alarms(ecs_cluster)
        md_output += alarm_str

    if ecs_cluster.services:
        svc_str = await asyncio.gather(*[md_ecs_service_summary(service, display_alarms, display_service_events)
                                         for service in ecs_cluster.services])
        md_output += ''.join(svc_str)

    return md_output
