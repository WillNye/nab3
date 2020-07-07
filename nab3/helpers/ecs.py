from double_click import echo
from double_click.markdown import generate_md_bullet_str, generate_md_table_str


def display_ecs_service_summary(ecs_service):
    """

    :param ecs_service: ECSService object
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
    md_output = f"# {ecs_service.name}\n{generate_md_bullet_str(bullets)}\n## Events"
    headers = ["Event", "Occurred At"]
    rows = [[event.get('message'), event.get('created_at')] for event in ecs_service.events]
    echo(f"{md_output}{generate_md_table_str(rows, headers)}")
