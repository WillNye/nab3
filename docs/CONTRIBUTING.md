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

If the field wasn't already provided as part of a mixin it will need to be created on init.
Here is a snippet to illustrate how this is done:
```python
class ECSCluster:
    def __init__(self, **kwargs):
        """
        field_name: name of the attribute for the instance
        service_class: Name of the Service class as defined within BaseAWS._service_map
        """
        self.create_service_field(field_name='asg', service_class='asg')
        self.create_service_field(field_name='instances', service_class='ecs_instance')
        self.create_service_field(field_name='services', service_class='ecs_service')
        super(self._get_service_class('ecs_cluster'), self).__init__(**kwargs)
```
 
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

### boto3_client_name (required)
The value used when creating the boto3 client.

For example, if the describe operation for a service class would typically require something like `client = boto3.client('autoscaling')`. Then `boto3_client_name = 'autoscaling'`

### key_prefix (required)
The prefix used to identify a service from a related service's boto3 response.

Take this snippet of the describe_autoscaling_groups response syntax. 
Note how the attributes are prefixed with the service they represent.
* `AutoScalingGroup`
* `LaunchConfiguration`
* `LaunchTemplate`

Following this example. 
If you're setting the key_prefix for the launch config service class key_prefix will be set to the value it is referenced as.
 
This should be immediately obvious based on the response syntax in the api reference but it will be things like the name, and arn.

The response for those keys according the api ref is `LaunchConfigurationName` so `key_prefix = 'LaunchConfiguration'` for the `LaunchConfiguration` service class.

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

### client_id (optional)
By default `client_id = key_prefix` but sometimes the service's describe call has its own convention for some reason.
An example of this is Security Groups. Security groups are referred to as `SecurityGroup` in every boto3 response, except describe_security_groups.
As you can see by the response syntax snippet below, a Security Group attribute is instead referred to as `Group`. Hence the need for `client_id`. 
Don't shoot the messenger.

```json
{
    "SecurityGroups": [
        {
            "Description": "string",
            "GroupName": "string",
            "GroupId": "string",
            "OwnerId": "string"
        }
    ]
}
```

### _boto3_describe_def (required)
A dict used to define the service class' boto3 describe call.

The keys for the dict:
#### client_call str: default `f'describe_{camel_to_snake(self.key_prefix)}s'`
This is the name of the describe call

#### response_key str: default `f'{self.key_prefix}s'` 
The key within the boto3 response which contains the desired output.
A response from boto3 is wrapped within a secondary dict that contains 2+ keys.
* The first is `NextToken`
* Look for the one within the API ref docs containing the output, that's what this value should be.

#### call_params dict: default `dict()`
The parameters that are passed to the boto3 call.
> Using snake case is heavily encouraged for consistency but not required
    
params within the dict should be structured as such `variable_name: str = dict(name:str, type:any, default:any=None)`.
The purpose of this is to not only validate the request but to also perform any necessary normalization. 

### _boto3_list_def (required*)
This method is only required if the service contains a boto3.client.list function. 
This method is effectively identical to `boto3_describe_def` the only caveat is this is for the list call. 

### _to_boto3_case (optional)
boto3 will switch between `camelBack` and `CamelCap` from one service to the next. 
This variable makes the service class aware of which type should be expected.

This value uses 1 of 2 helper functions within nab3. `snake_to_camelback` or `snake_to_camelcap`.
`to_boto3_case` defaults to `snake_to_camelback` so this should only need to be defined within a service class if the boto3 response is camelcap.
In which case, this value should be set to `_to_boto3_case = snake_to_camelcap`

### _response_alias (optional)
Very rarely, a boto3 response will contain a key that doesn't follow the same naming standard as outlined earlier. 
An example of this is `describe_security_groups` which contains a key called `user_id_group_pairs`.
`user_id_group_pairs` are the SG rules for a security group but it also contains the Security Group for the rule.
This provides a mechanism to support this exact scenario.

The key(s) for `_response_alias` is the name of key as it is within the boto3 response.
The value is the service's key representation within `BaseAWS._service_map`.
So, for this example `_response_alias = dict(user_id_group_pairs='security_group')`

If you're thinking this kind of sounds like `client_id` there is one major distinction. 
While both the `client_id` and `_response_alias` will normalize the key, `_response_alias` also updates the attribute to be an instance service class of the defined type 

## Wiring it up
Earlier in the doc there was a reference to `BaseAWS._service_map`.
For a service to be discoverable for get/list operations as well as casting a related service responses' output to an instance of the new service class the `BaseAWS._service_map` must be updated to include it.

This process is incredibly straight forward. 
The key is an arbitrary identifier used to call the service within an `AWS` instance.
The value is the class name as a string, e.g. the `LoadBalancer` class would be `'LoadBalancer'`

## Next steps
If you still have questions for more advanced scenarios look at the following service classes.
Each of these classes illustrate different complex use cases.

* ASG
* EC2Instance
* ECSCluster

