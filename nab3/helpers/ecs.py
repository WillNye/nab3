from double_click import echo
from double_click.markdown import generate_md_bullet_str, generate_md_table_str

from nab3.helpers.alerts import generated_md_alerts


def md_ecs_service_summary(ecs_service, display_alerts=True, display_events=True):
    """

    :param ecs_service: ECSService object
    :param display_events: bool Default(True) - Display the 50 most recent events of the service
    :return:
    """
    ecs_service.load()

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
        rows = [[event.get('message'), event.get('created_at')] for event in ecs_service.events]
        md_output += f"\n## Events{generate_md_table_str(rows, headers)}"

    if display_alerts:
        md_output += generated_md_alerts(ecs_service, include_name=False)

    return md_output


def display_ecs_service_summary(ecs_service, display_alerts=True, display_events=True):
    """

    :param ecs_service: ECSService object
    :param display_events: bool Default(True) - Display the 50 most recent events of the service
    :return:
    """
    echo(md_ecs_service_summary(ecs_service, display_alerts, display_events))


def display_ecs_cluster_summary(ecs_cluster, display_cloudwatch_alarms=False, display_service_events=False):
    """

    :param ecs_cluster: ECSCluster object
    :param display_cloudwatch_alarms: bool Default(False) - Display cluster cloudwatch alarms for the last 30 days
    :param display_service_events: bool Default(False) - Display the 50 most recent events of each service
    :return:
    """
    ecs_cluster.load()
