# Contributing to nab3
Any help extending nab3 is welcome and to make that a little easier this will help shed some light on how to create a Service class in nab3.

## Mixins and the base class

### BaseService or PaginatedBaseService
The distinction between the `BaseService` class and the `PaginatedBaseService` is the `Service.list` implementation.  

#### BaseService
A service that inherits from `BaseService` has a list operation in boto3. 
An example of this would be boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_clusters.
The list response size is much smaller but as a result much faster. It contains minimal information about the service.
The response from the list operation is split up into a list of calls to the describe operation which are then ran async.
Performance gains from making the describe operation async more than make up for the upfront call to the list operation.

#### PaginatedBaseService
With all of that said, you can probably infer that a service that inherits from `PaginatedBaseService` DOES NOT have a list operation in boto3. 
This means that `Service.list` calls to it will be synchronous for large requests like listing all ec2 instances. 

### Mixins
nab3 provides several mixins that typically fulfill one of two purposes
 
#### Adding attributes to a service that are not part of the boto3 response 
An example of this would be adding the `SecurityGroupMixin` to the `LoadBalancer` class.
I constantly find myself looking at the inbound rules for an ALB because it's kind of important to know has access to an ALB.
A list of security groups aren't traditionally available with describe_load_balancers call in boto3 so add the SG mixin.
It will create the attribute on init and provide a method named `load_${attribute_name}`.
That method is used to retrieve the attribute (in this case the ASG SGs) and set the value for the instance.
The method doesn't need to be called explicitly, the attribute will also be retrievable using the following calls:
* `await load_balancer.fetch('security_groups')`
* `await nab3_aws_obj.load_balancer.get(name='lb_name', with_related=['security_groups'])`

While a default load method is provided, if it doesn't meet the needs of the class being implemented, you can override the load method.
There are several examples of how and why the load method would need to be overridden including `ASG.load_security_groups`.
 
#### Exposing helper methods to retrieve reporting info for the service instance
The most common examples of these are getting cloud watch alerts or metrics such as CPU Utilization.
```python
from nab3 import AWS as NabAWS
asg = await NabAWS.load_balancer.get(name='lb_name')
stats = asg.get_statistics(metric_name='CPUUtilization', statistics=['Average', 'Maximum'], interval_as_seconds=300)
``` 

## Docstring
Outside of common sense, please include the boto3 api doc to the details and list (if list exists) operation.
This will be somewhere in `boto3.amazonaws.com/v1/documentation/api/latest/reference/services`

## Class variables

### boto3_service_name (required)
The value used when creating the boto3 client.

For example, if the describe operation for a service class would typically require something like `client = boto3.client('autoscaling')`. Then `boto3_service_name = 'autoscaling'`

### client_id (required)
The prefix used to identify service attributes within the boto3 response.

Take this snippet of the describe_autoscaling_groups response syntax. 
Note how the attributes are prefixed with the service they represent.
* `AutoScalingGroup`
* `LaunchConfiguration`
* `LaunchTemplate`

Following this example. 
If you're calling `describe_autoscaling_groups` the client_id will be the prefix to identify attributes that are unique to each ASG.

This should be immediately obvious based on the response syntax in the api reference but it will be things like the name, and arn.

The response for those keys according the api ref is `AutoScalingGroup` so `client_id = 'AutoScalingGroup'`

```json
{
    "AutoScalingGroupName": "string",
    "AutoScalingGroupARN": "string",
    "LaunchConfigurationName": "string",
    "LaunchTemplate": {
        "LaunchTemplateId": "string",
        "LaunchTemplateName": "string",
        "Version": "string"
    }
}
```

### _boto3_describe_def (required)


### _boto3_list_def (optional)


### _to_boto3_case (optional)


### _response_alias (optional)


### key_prefix (optional)



