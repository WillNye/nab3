# nab3 (Not Another Boto3)
Put simply, nab3 provides an interface to easily inspect and search an AWS resource and its related resources.

Boto3 is great for pulling information for a single resource when you know exactly what you're looking for. 
Unfortunately, if you don't know that exact resource and need to deviate in any way the complexity to retrieve that resource is, in all honesty, insane.

For example, what if you need to get the security groups for an ECS Cluster?
>This sounds simple, and is a real world scenario I've ran into many times. 

These are the steps using boto3
* Create an ecs client
* Call describe_container_instances
* Pull the ec2InstanceId
* Create an autoscaling client
* Call describe_auto_scaling_instances and pass in an ec2InstanceId
* Pull the AutoScalingGroupName
* Call describe_auto_scaling_groups and pass in the AutoScalingGroupName
* Pull the LaunchConfigurationName
* Call describe_launch_configurations and pass in  the LaunchConfigurationName
* FINALLY you have the SecurityGroups jk, it's just the ID
* Create an ec2 client
* Call describe_security_groups

In nab3?
```python
import asyncio

from nab3 import AWS


async def ecs_sg_example():
    ecs_cluster = await aws.ecs_cluster.get(name='cluster-name', with_related=['asg__security_groups'])
    # print([sg.name for sg in ecs_cluster.security_groups])


aws = AWS()
asyncio.run(ecs_sg_example())

```




