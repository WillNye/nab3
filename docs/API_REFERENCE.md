- [ nab3.aws ](#nab3.aws_3801544942586391635)
	- [ nab3.aws.AWS ](#nab3.aws.AWS_8129102527065309338)
		- [ AWS.service_options ](#AWS.service_options_5848187387314332113)
- [ nab3.helpers.cloud_watch ](#nab3.helpers.cloud_watch_1986397987241252659)
	- [ md_alarms ](#md_alarms_1398556722723986265)
	- [ md_statistics_summary ](#md_statistics_summary_5469896894287487513)
	- [ set_n_service_stats ](#set_n_service_stats_2285603431245394564)
	- [ set_service_stats ](#set_service_stats_3696365076828464804)
- [ nab3.helpers.ec2 ](#nab3.helpers.ec2_2836875331105255328)
	- [ md_autoscale_ips ](#md_autoscale_ips_7044935364021548471)
	- [ md_autoscale_sgs ](#md_autoscale_sgs_5907407289189221801)
	- [ md_security_group_table ](#md_security_group_table_4041352014948605449)
- [ nab3.helpers.ecs ](#nab3.helpers.ecs_8362314369377000401)
	- [ md_ecs_cluster_summary ](#md_ecs_cluster_summary_4447824367297390828)
	- [ md_ecs_service_summary ](#md_ecs_service_summary_4738500638420619465)
- [ nab3.service ](#nab3.service_3711737182203522260)
	- [ nab3.service.ASG ](#nab3.service.ASG_986818970620613850)
		- [ ASG.load_security_groups ](#ASG.load_security_groups_5848187387314332113)
	- [ nab3.service.Alarm ](#nab3.service.Alarm_6508720122460064027)
	- [ nab3.service.AppAutoScalePolicy ](#nab3.service.AppAutoScalePolicy_1262979988893200355)
		- [ AppAutoScalePolicy.get_alarms ](#AppAutoScalePolicy.get_alarms_5701525941751542591)
	- [ nab3.service.AutoScalePolicy ](#nab3.service.AutoScalePolicy_3191251194611477573)
		- [ AutoScalePolicy.get_alarms ](#AutoScalePolicy.get_alarms_6488420976853236330)
	- [ nab3.service.EC2Instance ](#nab3.service.EC2Instance_8095221286791516216)
	- [ nab3.service.ECSCluster ](#nab3.service.ECSCluster_7942029921343694546)
		- [ ECSCluster.load_asg ](#ECSCluster.load_asg_3179665470232192586)
		- [ ECSCluster.load_instances ](#ECSCluster.load_instances_7828236837344479429)
		- [ ECSCluster.load_scaling_policies ](#ECSCluster.load_scaling_policies_7268273482920819292)
		- [ ECSCluster.load_services ](#ECSCluster.load_services_172548728713415266)
	- [ nab3.service.ECSInstance ](#nab3.service.ECSInstance_7448764810667774705)
	- [ nab3.service.ECSService ](#nab3.service.ECSService_3337171372682786165)
	- [ nab3.service.ECSTask ](#nab3.service.ECSTask_4641927277165331217)
	- [ nab3.service.ElasticacheCluster ](#nab3.service.ElasticacheCluster_5598746375371897558)
	- [ nab3.service.LaunchConfiguration ](#nab3.service.LaunchConfiguration_567936306148641779)
	- [ nab3.service.LoadBalancer ](#nab3.service.LoadBalancer_7131441081920965684)
	- [ nab3.service.LoadBalancerClassic ](#nab3.service.LoadBalancerClassic_9151006587796763035)
	- [ nab3.service.Metric ](#nab3.service.Metric_2840362187949968031)
	- [ nab3.service.Pricing ](#nab3.service.Pricing_7492738244719239801)
	- [ nab3.service.SecurityGroup ](#nab3.service.SecurityGroup_2898155570107013884)
- [ nab3.utils ](#nab3.utils_286332590025259175)
	- [ camel_to_kebab ](#camel_to_kebab_4608132556393518212)
	- [ camel_to_snake ](#camel_to_snake_6730699021901936102)
	- [ describe_resource ](#describe_resource_6896802395403692361)
	- [ paginated_search ](#paginated_search_5541035285911710010)
	- [ snake_to_camelback ](#snake_to_camelback_5314572791684370087)
	- [ snake_to_camelcap ](#snake_to_camelcap_3657068322267849616)
- [ nab3.mixin ](#nab3.mixin_7599287130512564525)
	- [ nab3.mixin.AppAutoScaleMixin ](#nab3.mixin.AppAutoScaleMixin_7927862042798220131)
		- [ AppAutoScaleMixin.load_scaling_policies ](#AppAutoScaleMixin.load_scaling_policies_5095813452614344694)
	- [ nab3.mixin.AutoScaleMixin ](#nab3.mixin.AutoScaleMixin_4604874938193143041)
		- [ AutoScaleMixin.load_scaling_policies ](#AutoScaleMixin.load_scaling_policies_6459525290886647683)
	- [ nab3.mixin.MetricMixin ](#nab3.mixin.MetricMixin_7099649773583629005)
		- [ MetricMixin.get_available_metrics ](#MetricMixin.get_available_metrics_5519894459235699989)
		- [ MetricMixin.get_metric_options ](#MetricMixin.get_metric_options_6414583743980913860)
		- [ MetricMixin.get_statistics ](#MetricMixin.get_statistics_2492068404772345131)
	- [ nab3.mixin.SecurityGroupMixin ](#nab3.mixin.SecurityGroupMixin_4723764845411956004)
		- [ SecurityGroupMixin.load_accessible_resources ](#SecurityGroupMixin.load_accessible_resources_6154904041039139227)


<a name="nab3.aws_3801544942586391635"></a>
## nab3.aws

<a name="nab3.aws.AWS_8129102527065309338"></a>
### nab3.aws.AWS(self, session: boto3.session.Session = Session(region_name='us-east-1'))

Connection manager tied to a boto3 session instance.
When a Service.list/get method is called a boto3 client is lazy loaded into the AWS instance and is used by any other services that required that same client.

<a name="AWS.service_options_5848187387314332113"></a>
#### `AWS.service_options() -> list`

Returns a list of supported service classes
`:return: list<str>`

<a name="nab3.helpers.cloud_watch_1986397987241252659"></a>
## nab3.helpers.cloud_watch
    

<a name="md_alarms_1398556722723986265"></a>
#### `md_alarms(scalable_object, start_date=datetime.datetime(2020, 8, 11, 9, 35, 58, 35700), end_date=datetime.datetime(2020, 9, 10, 9, 35, 58, 35716)) -> str`

Generate a markdown summary of alarms for a scalable object.

Example:
```python
ecs_cluster = await AWS.ecs_cluster.get(name='sample', with_related=[
                                            'asg', 'scaling_policies', 'services', 'services__scaling_policies'
                                        ])
md_output = f"# {ecs_cluster.name}"
alarm_str = await md_alarms(ecs_cluster)

with open(f'{ecs_cluster.name}.md', 'w') as f:
    f.write(f'{md_output}/n{alarm_str}')
```

<a name="md_statistics_summary_5469896894287487513"></a>
#### `md_statistics_summary(metric_obj_list: list, include_table: bool = True) -> str`

Creates a markdown summary based on the provided get_statistics list response

    :param metric_obj_list:
    :param metric_name:
    :param include_table: Include an md table containing the datapoints used to generate the summary.
        Columns: Time Unit Average Maximum
    :return:
    

<a name="set_n_service_stats_2285603431245394564"></a>
#### `set_n_service_stats(service_list, stat_list: list = None, start_date=datetime.datetime(2020, 8, 11, 9, 35, 58, 35723), end_date=datetime.datetime(2020, 9, 10, 9, 35, 58, 35725))`

Retrieves all statistics passed in stat_list for each of the provided services in service_list.

    For each in service_list: service_obj.stats = [dict(metric=str, stats=Metric())]

    :param service_list:
    :param stat_list:
    :param start_date:
    :param end_date:
    :return: service_list
    

<a name="set_service_stats_3696365076828464804"></a>
#### `set_service_stats(service_obj, stat_list: list = None, start_date=datetime.datetime(2020, 8, 11, 9, 35, 58, 35719), end_date=datetime.datetime(2020, 9, 10, 9, 35, 58, 35721))`

Retrieves all statistics passed in stat_list for the service_obj.

    service_obj.stats = [dict(metric=str, stats=Metric())]

    :param service_obj:
    :param stat_list:
    :param start_date:
    :param end_date:
    :return: service_obj


<a name="nab3.helpers.ec2_2836875331105255328"></a>
## nab3.helpers.ec2
    

<a name="md_autoscale_ips_7044935364021548471"></a>
#### `md_autoscale_ips(asg_object)`

Creates a md table str containing all instances with their IPs for an scalable object

<a name="md_autoscale_sgs_5907407289189221801"></a>
#### `md_autoscale_sgs(asg_object)`

Creates a md summary for a scalable object containing all security groups, the objects' SG rules, and the SG rules of services it has access to

<a name="md_security_group_table_4041352014948605449"></a>
#### `md_security_group_table(sg_list: list, id_filter: list = [], is_accessible_resources: bool = False)`

Creates a md table str for a list of security groups that contains the SG rules for each SG


<a name="nab3.helpers.ecs_8362314369377000401"></a>
## nab3.helpers.ecs

<a name="md_ecs_cluster_summary_4447824367297390828"></a>
#### `md_ecs_cluster_summary(ecs_cluster, display_alarms=True, display_service_events=False) -> str`


    :param ecs_cluster: ECSCluster object
    :param display_alarms: bool Default(True) - Display cloudwatch alarms for the last 30 days
    :param display_service_events: bool Default(True) - Display the 50 most recent events of each service
    :return:
    

<a name="md_ecs_service_summary_4738500638420619465"></a>
#### `md_ecs_service_summary(ecs_service, display_alarms=True, display_events=True) -> str`


    :param ecs_service: ECSService object
    :param display_alarms: bool Default(True) - Display service cloudwatch alarms for the last 30 days
    :param display_events: bool Default(True) - Display the 50 most recent events of the service
    :return:
    

<a name="nab3.service_3711737182203522260"></a>
## nab3.service

<a name="nab3.service.ASG_986818970620613850"></a>
### nab3.service.ASG(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_auto_scaling_groups
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    

<a name="ASG.load_security_groups_5848187387314332113"></a>
#### `ASG.load_security_groups(self)`

Retrieves the instances related security groups.

        stored as the instance attribute `obj.security_groups`

        :return: list<SecurityGroup>
        

<a name="nab3.service.Alarm_6508720122460064027"></a>
### nab3.service.Alarm(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.describe_alarm_history
    

<a name="nab3.service.AppAutoScalePolicy_1262979988893200355"></a>
### nab3.service.AppAutoScalePolicy(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/application-autoscaling.html#ApplicationAutoScaling.Client.describe_scaling_policies
    
    Scalable Dimension options:
        ecs:service:DesiredCount
        ec2:spot-fleet-request:TargetCapacity
        elasticmapreduce:instancegroup:InstanceCount
        appstream:fleet:DesiredCapacity
        dynamodb:table:ReadCapacityUnits
        dynamodb:table:WriteCapacityUnits
        dynamodb:index:ReadCapacityUnits
        dynamodb:index:WriteCapacityUnits
        rds:cluster:ReadReplicaCount
        sagemaker:variant:DesiredInstanceCount
        custom-resource:ResourceType:Property 
        comprehend:document-classifier-endpoint:DesiredInferenceUnits
        lambda:function:ProvisionedConcurrency
        cassandra:table:ReadCapacityUnits
        cassandra:table:WriteCapacityUnits
    

<a name="AppAutoScalePolicy.get_alarms_5701525941751542591"></a>
#### `AppAutoScalePolicy.get_alarms(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True)`


        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        

<a name="nab3.service.AutoScalePolicy_3191251194611477573"></a>
### nab3.service.AutoScalePolicy(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_policies
    

<a name="AutoScalePolicy.get_alarms_6488420976853236330"></a>
#### `AutoScalePolicy.get_alarms(self, start_date, end_date, item_type=None, alarm_types=[], sort_desc=True)`


        :param start_date: StartDate=datetime(2015, 1, 1)
        :param end_date: EndDate=datetime(2015, 1, 1)
        :param item_type: HistoryItemType='ConfigurationUpdate StateUpdate Action'
        :param alarm_types: AlarmTypes=['CompositeAlarm MetricAlarm']
        :param sort_desc: bool -> ScanBy='TimestampDescending TimestampAscending'
        :return:
        

<a name="nab3.service.EC2Instance_8095221286791516216"></a>
### nab3.service.EC2Instance(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances

<a name="nab3.service.ECSCluster_7942029921343694546"></a>
### nab3.service.ECSCluster(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_clusters
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_clusters

<a name="ECSCluster.load_asg_3179665470232192586"></a>
#### `ECSCluster.load_asg(self)`

Retrieves the instances asg.

        stored as the instance attribute `obj.asg`

        if self.scaling_policies.loaded:
            return self.scaling_policies

        if not self.security_groups.loaded:
            await self.fetch('security_groups')

        filter_list = [sg.id for sg in self.security_groups]
        if not filter_list:
            return self.accessible_resources

        self.accessible_resources = await self.accessible_resources.service_class.list(Filters=[dict(
            Name='ip-permission.group-id',
            Values=filter_list
        )])

        return self.accessible_resources

        :return: ASG
        

<a name="ECSCluster.load_instances_7828236837344479429"></a>
#### `ECSCluster.load_instances(self)`

Retrieves the cluster's instances.

        stored as the instance attribute `obj.instances`

        :return: list<instances>
        

<a name="ECSCluster.load_scaling_policies_7268273482920819292"></a>
#### `ECSCluster.load_scaling_policies(self)`

Retrieves the cluster's scaling policies.

        stored as the instance attribute `obj.scaling_policies`

        :return: list<scaling_policies>
        

<a name="ECSCluster.load_services_172548728713415266"></a>
#### `ECSCluster.load_services(self)`

Retrieves the cluster's services.

        stored as the instance attribute `obj.services`

        :return: list<services>
        

<a name="nab3.service.ECSInstance_7448764810667774705"></a>
### nab3.service.ECSInstance(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_container_instances
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_container_instances

    For filter see docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-query-language.html but...
        It appears to be client side so it's likely easier to use nab3.Filter

    Valid status options:
        ACTIVE
        DRAINING
        REGISTERING
        DEREGISTERING
        REGISTRATION_FAILED
    

<a name="nab3.service.ECSService_3337171372682786165"></a>
### nab3.service.ECSService(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_services
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services

<a name="nab3.service.ECSTask_4641927277165331217"></a>
### nab3.service.ECSTask(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.list_tasks
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_tasks
    

<a name="nab3.service.ElasticacheCluster_5598746375371897558"></a>
### nab3.service.ElasticacheCluster(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_cache_clusters
    

<a name="nab3.service.LaunchConfiguration_567936306148641779"></a>
### nab3.service.LaunchConfiguration(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_launch_configurations
    

<a name="nab3.service.LoadBalancer_7131441081920965684"></a>
### nab3.service.LoadBalancer(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    

<a name="nab3.service.LoadBalancerClassic_9151006587796763035"></a>
### nab3.service.LoadBalancerClassic(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.describe_load_balancers
    

<a name="nab3.service.Metric_2840362187949968031"></a>
### nab3.service.Metric(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.list_metrics
    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics
    docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#dimension-combinations
    

<a name="nab3.service.Pricing_7492738244719239801"></a>
### nab3.service.Pricing(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/pricing.html#Pricing.Client.get_products
    

<a name="nab3.service.SecurityGroup_2898155570107013884"></a>
### nab3.service.SecurityGroup(self, **kwargs)


    boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_security_groups
    

<a name="nab3.utils_286332590025259175"></a>
## nab3.utils

<a name="camel_to_kebab_4608132556393518212"></a>
#### `camel_to_kebab(str_obj: str) -> str`

Convert a string from camel case to kebab case

<a name="camel_to_snake_6730699021901936102"></a>
#### `camel_to_snake(str_obj: str) -> str`

Convert a string from camel case to snake case

<a name="describe_resource_6896802395403692361"></a>
#### `describe_resource(search_fnc, id_key: str, id_list: list, search_kwargs: dict, chunk_size: int = 50) -> list`

Chunks up describe operation and runs requests concurrently.

    :param search_fnc: Name of the boto3 function e.g. describe_auto_scaling_groups
    :param id_key: Name of the key used for describe operation e.g. AutoScalingGroupNames
    :param id_list: List of id values
    :param search_kwargs: Additional arguments to pass to the describe operation like Filter, MaxRecords, or Tags
    :param chunk_size: Used to set request size. Cannot exceed the operation's MaxRecords or there may be data loss.
    :return: list<boto3 describe response>
    

<a name="paginated_search_5541035285911710010"></a>
#### `paginated_search(search_fnc, search_kwargs: dict, response_key: str, max_results: int = None) -> list`

Retrieve and aggregate each paged response, returning a single list of each response object
    :param search_fnc:
    :param search_kwargs:
    :param response_key:
    :param max_results:
    :return:
    

<a name="snake_to_camelback_5314572791684370087"></a>
#### `snake_to_camelback(str_obj: str) -> str`

Convert a string from snake_case to camelBack

<a name="snake_to_camelcap_3657068322267849616"></a>
#### `snake_to_camelcap(str_obj: str) -> str`

Convert a string from snake_case to CamelCap

<a name="nab3.mixin_7599287130512564525"></a>
## nab3.mixin

<a name="nab3.mixin.AppAutoScaleMixin_7927862042798220131"></a>
### nab3.mixin.AppAutoScaleMixin(self, **kwargs)

Mixin to provide app auto scale integrations for a service class

<a name="AppAutoScaleMixin.load_scaling_policies_5095813452614344694"></a>
#### `AppAutoScaleMixin.load_scaling_policies(self)`

<a name="nab3.mixin.AutoScaleMixin_4604874938193143041"></a>
### nab3.mixin.AutoScaleMixin(self, **kwargs)

<a name="AutoScaleMixin.load_scaling_policies_6459525290886647683"></a>
#### `AutoScaleMixin.load_scaling_policies(self)`

<a name="nab3.mixin.MetricMixin_7099649773583629005"></a>
### nab3.mixin.MetricMixin(self, /, *args, **kwargs)

<a name="MetricMixin.get_available_metrics_5519894459235699989"></a>
#### `MetricMixin.get_available_metrics(self)`

<a name="MetricMixin.get_metric_options_6414583743980913860"></a>
#### `MetricMixin.get_metric_options(self)`

<a name="MetricMixin.get_statistics_2492068404772345131"></a>
#### `MetricMixin.get_statistics(self, metric_name: str, start_time: datetime.datetime = datetime.datetime(2020, 9, 10, 11, 35, 57, 758116), end_time: datetime.datetime = datetime.datetime(2020, 9, 10, 14, 35, 57, 758129), interval_as_seconds: int = 300, **kwargs) -> list`


        :param metric_name:
        :param start_time:
        :param end_time:
        :param interval_as_seconds:
        :param kwargs:
        :return:
        

<a name="nab3.mixin.SecurityGroupMixin_4723764845411956004"></a>
### nab3.mixin.SecurityGroupMixin(self, **kwargs)

<a name="SecurityGroupMixin.load_accessible_resources_6154904041039139227"></a>
#### `SecurityGroupMixin.load_accessible_resources(self)`

