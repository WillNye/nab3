import asyncio
import copy
import logging
import re
import sys
from itertools import chain
from collections import defaultdict

import boto3
import botocore

from nab3.utils import (
    camel_to_snake, describe_resource, paginated_search, snake_to_camelback
)

LOGGER = logging.getLogger('nab3')
LOGGER.setLevel(logging.WARNING)


class ClientHandler:
    """Maintains state of N different boto3 client connections
    """

    def __init__(self, session: boto3.Session = boto3.Session(),
                 default_config: botocore.client.Config = botocore.client.Config(max_pool_connections=10)):
        self._botocore_config = default_config
        self._session = session
        self._account = None

    def get(self, service_name):
        """Retrieves the client resource object.
        Clients are set using the object's session lazily.

        :param service_name:
        :return:
        """
        service = getattr(self, service_name, None)
        if not service:
            service = self._session.client(service_name, config=copy.deepcopy(self._botocore_config))
            setattr(self, service_name, service)
        return service

    @property
    def region(self):
        return self._session.region_name

    @property
    def account(self):
        if not self._account:
            sts_client = self.get('sts')
            response = sts_client.get_caller_identity()
            self._account = response['Account']

        return self._account


class BaseAWS:
    _client: ClientHandler
    loaded_service_classes = {}
    _service_map = dict(
        alarm='Alarm',
        app_scaling_policy='AppAutoScalePolicy',
        asg='ASG',
        ecs_cluster='ECSCluster',
        ecs_instance='ECSInstance',
        ecs_service='ECSService',
        ecs_task='ECSTask',
        elasticache_cluster='ElasticacheCluster',
        elasticache_node='ElasticacheNode',
        image='Image',
        instance='EC2Instance',
        kafka_cluster='KafkaCluster',
        kafka_broker='KafkaBroker',
        launch_configuration='LaunchConfiguration',
        load_balancer='LoadBalancer',
        load_balancer_classic='LoadBalancerClassic',
        metric='Metric',
        pricing='Pricing',
        rds_cluster='RDSCluster',
        rds_instance='RDSInstance',
        scaling_policy='AutoScalePolicy',
        security_group='SecurityGroup',
        target_group='TargetGroup'
    )

    @property
    def client(self):
        return self._client

    @property
    def region(self):
        return self._client.region

    def _get_service_class(self, service_name):
        service_class = self._service_map[service_name]
        class_name = f'{service_class}_x{str(id(self._client))}'
        loaded_service = self.loaded_service_classes.get(class_name)
        if loaded_service:
            return loaded_service

        class_ref = getattr(sys.modules['nab3.service'], service_class)
        new_class = type(
            class_name,
            class_ref.__bases__,
            dict(class_ref.__dict__, **dict(_client=self._client))
        )
        self.loaded_service_classes[class_name] = new_class

        return new_class


class ServiceWrapper:
    """A wrapper for Service objects to provide a consistent interface when dealing with 1 or more instances

    If you are familiar with Django this is the love child of the Field class and Queryset class.
    It provides a wrapper to filter, load, or fetch 1 or more service objects.
    Because the instance fields are set dynamically ServiceWrapper also:
        Validates the type for an instance attribute that is expected to be a Service object
        Allows attributes to behave like the object e.g. obj.service_attr.other_service_list.load()
    """

    def __init__(self, service_class, name: str = None):
        self.service_class = service_class
        self.service = None

        if name:
            self.__dict__['name'] = name

    def is_list(self) -> bool:
        return isinstance(self.service, list)

    def is_loaded(self):
        if self.service is None:
            return False
        elif self.is_list():
            return all(svc._loaded for svc in self.service)
        else:
            return self.service._loaded

    async def load(self, force: bool = False):
        if self.service:
            if self.is_list() and not self.is_loaded():
                self.service = await self.service_class.list(service_list=self.service)
            elif not self.is_loaded() or force:
                await self.service.load(force=force)
        return self.service

    async def fetch(self, *args, **kwargs):
        if self.service:
            if self.is_list():
                await asyncio.gather(*[svc.fetch(*args, **kwargs) for svc in self.service])
            else:
                await self.service.fetch(*args, **kwargs)
        return self.service

    def copy(self):
        service_obj = ServiceWrapper(self.service_class)
        service_obj.service = self.service
        return service_obj

    def __set_name__(self, owner, name):
        self.__dict__['name'] = name

    def __set__(self, obj, value) -> None:
        if isinstance(value, ServiceWrapper):
            value = value.service

        if isinstance(value, list):
            value = [v.service if isinstance(v, ServiceWrapper) else v for v in value]

        if (isinstance(value, list) and all(isinstance(elem_val, self.service_class) for elem_val in value))\
                or (not isinstance(value, list) and isinstance(value, self.service_class)):
            svc_wrapper = ServiceWrapper(service_class=self.service_class)
            svc_wrapper.service = value
            obj.__dict__[self.name] = svc_wrapper
        else:
            raise ValueError(f'{value} != (list<{self.service_class}> || {self.service_class})')

    def __setattr__(self, key, value):
        if key in ['service_class', 'service']:
            self.__dict__[key] = value
        elif not self.is_list():
            self.__dict__['service'].__dict__[key] = value
        else:
            raise ValueError(f'Unable to set {key} on multiple Service objects')

    def __getattr__(self, value):
        if value == 'loaded':
            return self.is_loaded()
        elif value == 'load':
            return self.load
        elif self.service is None or value in ['list', 'get']:
            return getattr(self.service_class, value, None)

        return getattr(self.service, value, None)

    def __getitem__(self, item):
        if self.is_list():
            svc_wrapper = ServiceWrapper(service_class=self.service_class)
            svc_wrapper.service = self.service[item]
            return svc_wrapper
        else:
            raise TypeError('Service class is not subscriptable')

    def __iter__(self):
        if isinstance(self.service, list):
            for service in self.service:
                svc_wrapper = ServiceWrapper(service_class=self.service_class)
                svc_wrapper.service = service
                yield svc_wrapper
        elif self.service is None or not self.is_loaded():
            yield from []
        else:
            raise TypeError(f"{self.service} is not iterable")

    def __len__(self):
        if self.service is None:
            return 0
        elif isinstance(self.service, list):
            return len(self.service)
        else:
            return 1

    def __bool__(self):
        return bool(self.is_loaded())


class Filter:
    """Provides a class to easily filter service objects using common operations like gt/lt, contains, exact, etc.

    The decision to have a filter class and a run method is to make the process of hitting AWS more explicit.
    It's also worth mentioning that lookups to AWS can get costly fast and this helps to mitigate that.
    This is also why there's no filter method Service class.
    nab3 is designed so all necessary data is pulled at once and manipulated through out the script.

    For example, if you wanted to get ECS Cluster stats grouped by dev, stg, and prod:

    ecs_cluster = await AWS.ecs_cluster.list()
    f_prod = Filter(name__icontains_any=['prod-', 'production'])
    f_stg = Filter(name__icontains_any=['stg-', 'staging'])
    f_dev = Filter(name__icontains_any=['dev-', 'development'])
    prod_clusters = await f.run(ecs_cluster)
    stg_clusters = await f.run(ecs_cluster)
    dev_clusters = await f.run(ecs_cluster)

    # If this was an allowed method, the unassuming eye would think these were the same.
    # Surprise! The number of lookups is 3n (if there were a dev and stg equivalent for each prod cluster)
    prod_clusters = await AWS.ecs_cluster.filter(name__icontains_any=['prod-', 'production'])
    stg_clusters = await AWS.ecs_cluster.filter(name__icontains_any=['stg-', 'staging'])
    dev_clusters = await AWS.ecs_cluster.filter(name__icontains_any=['dev-', 'development'])

    Why? Because these evaluations are done as part of nab3 and are not supported by boto3 or the AWS API.
    """

    def __init__(self, **kwargs):
        self.filter_params = kwargs

    def upsert_filter(self, **kwargs):
        """Updates or creates Filter instance params used for filtering a Service object

        :param kwargs:
        :return:
        """
        for k, v in kwargs.items():
            self.filter_params[k] = v
        return self

    async def _match(self, service_obj, param_as_list, filter_value) -> tuple:
        """

        :param service_obj:
        :param param_as_list:
        :param filter_value:
        :return:
        """
        is_match = False
        safe_params = copy.deepcopy(param_as_list)  # Cause safety first
        if len(safe_params) > 1:
            if isinstance(service_obj, list) or (isinstance(service_obj, ServiceWrapper) and service_obj.is_list()):
                hits = await asyncio.gather(*[
                    self._match(e, safe_params, filter_value) for e in service_obj
                ])

                service_obj = [hit[0] for hit in hits]
                # If 1 gets in they all get in because this indicates the primary object is a match
                is_match = any(hit[1] for hit in hits)

            elif service_obj:
                cur_key = safe_params.pop(0)
                if isinstance(service_obj, dict):
                    obj_val = service_obj.get(cur_key)
                    response, is_match = await self._match(obj_val, safe_params, filter_value)
                    service_obj[cur_key] = response
                elif isinstance(service_obj, ServiceWrapper):
                    try:
                        await service_obj.load()
                        nested_obj = getattr(service_obj, cur_key)
                        response, is_match = await self._match(nested_obj, safe_params, filter_value)
                        setattr(service_obj, cur_key, response)
                    except AttributeError as ae:
                        LOGGER.warning(f'Await Service Object Error {ae} {service_obj} {cur_key} {safe_params}')

            return service_obj, is_match
        else:
            operation = safe_params[0]
            if service_obj and (operation.endswith('_any') or operation.endswith('_all')):
                assert isinstance(filter_value, list)

            try:
                if service_obj is None:
                    return service_obj, False
                elif operation in ['re', 're_any', 're_all']:
                    if operation == 're':
                        return service_obj, bool(re.match(filter_value, service_obj))
                    elif operation == 're_any':
                        return service_obj, any(bool(re.match(f_val, service_obj)) for f_val in filter_value)
                    else:
                        return service_obj, all(bool(re.match(f_val, service_obj)) for f_val in filter_value)

                elif operation in ['contains', 'contains_any', 'contains_all']:
                    if operation == 'contains':
                        return service_obj, bool(filter_value in service_obj)
                    elif operation == 'contains_any':
                        return service_obj, any(bool(f_val in service_obj) for f_val in filter_value)
                    else:
                        return service_obj, all(bool(f_val in service_obj) for f_val in filter_value)

                elif operation in ['icontains', 'icontains_any', 'icontains_all']:
                    lower_obj = service_obj.lower()
                    if operation == 'icontains':
                        return service_obj, bool(filter_value.lower() in lower_obj)
                    elif operation == 'icontains_any':
                        return service_obj, any(bool(f_val.lower() in lower_obj) for f_val in filter_value)
                    else:
                        return service_obj, all(bool(f_val.lower() in lower_obj) for f_val in filter_value)

                elif operation in ['exact', 'exact_any', 'exact_all']:
                    if operation == 'exact':
                        return service_obj, bool(filter_value == service_obj)
                    elif operation == 'exact_any':
                        return service_obj, any(bool(f_val == service_obj) for f_val in filter_value)
                    else:
                        return service_obj, all(bool(f_val == service_obj) for f_val in filter_value)

                elif operation in ['iexact', 'iexact_any', 'iexact_all']:
                    lower_obj = service_obj.lower()
                    if operation == 'iexact':
                        return service_obj, bool(filter_value.lower() == lower_obj)
                    elif operation == 'iexact_any':
                        return service_obj, any(bool(f_val.lower() == lower_obj) for f_val in filter_value)
                    else:
                        return service_obj, all(bool(f_val.lower() == lower_obj) for f_val in filter_value)

                elif operation in ['startswith', 'startswith_any']:
                    if operation == 'startswith':
                        return service_obj, service_obj.startswith(filter_value)
                    else:
                        return service_obj, any(service_obj.startswith(f_val) for f_val in filter_value)

                elif operation in ['endswith', 'endswith_any']:
                    if operation == 'endswith':
                        return service_obj, service_obj.endswith(filter_value)
                    else:
                        return service_obj, any(service_obj.endswith(f_val) for f_val in filter_value)

                elif operation == 'lt':
                    return service_obj, bool(service_obj < filter_value)
                elif operation == 'lte':
                    return service_obj, bool(service_obj <= filter_value)
                elif operation == 'gt':
                    return service_obj, bool(service_obj > filter_value)
                elif operation == 'gte':
                    return service_obj, bool(service_obj >= filter_value)
                else:
                    raise KeyError(f'{operation} is not a valid Filter operation.\nOptions: {self.operations()}')
            except Exception as e:
                LOGGER.warning(str(e))
                return service_obj, False

    async def run(self, service_obj):
        """
        :param service_obj:
        :return:
        """
        service_obj = service_obj.copy()

        for filter_param, filter_value in self.filter_params.items():
            hits = await asyncio.gather(*[
                self._match(so, filter_param.split('__'), filter_value) for so in service_obj
            ])
            service_obj.service = [hit[0] for hit in hits if hit[1]]

        return service_obj

    @staticmethod
    def operations():
        base_operations = ['re', 'contains', 'icontains', 'exact', 'iexact']
        all_operations = ['lt', 'lte', 'gt', 'gte', 'startswith', 'startswith_any', 'endswith', 'endswith_any']
        all_operations += [f'{base_op}_any' for base_op in base_operations]
        all_operations += [f'{base_op}_all' for base_op in base_operations]
        return sorted(all_operations + base_operations)


class Exclude(Filter):

    async def run(self, service_obj):
        """
        :param service_obj:
        :return:
        """
        service_obj = service_obj.copy()

        for filter_param, filter_value in self.filter_params.items():
            hits = await asyncio.gather(*[
                self._match(so, filter_param.split('__'), filter_value) for so in service_obj
            ])
            service_obj.service = [hit[0] for hit in hits if not hit[1]]

        return service_obj


class BaseService(BaseAWS):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """
    boto3_client_name: str
    key_prefix: str
    client_id: str
    """_response_alias maps each element in the list to a service class.
    This is an effort to ensure proper mapping on nested objects.
        example: describe_security_groups contains UserIdGroupPairs
            Each element is essentially a security group with some extra metadata
    """
    _loaded = False
    _response_alias = {}
    _to_boto3_case = snake_to_camelback
    # These are in relation to the call within the boto3 client
    # Not all clients/resources have a list operation
    _boto3_describe_def = dict(
        # client_call: str default f'describe_{camel_to_snake(self.key_prefix)}s'
        # response_key: str default f'{self.key_prefix}s'
        call_params=dict(),  # variable_name: str = dict(name:str, type:any, default=None)
    )
    _boto3_list_def = dict(
        # client_call: str default f'list_{camel_to_snake(self.key_prefix)}s'
        # response_key: str default f'{self.key_prefix}Arns'
        call_params=dict(),  # variable_name: str = dict(name:str, type:any, default=None)
    )
    # sometimes the boto3 response is ugly, a misrepresentation of what a key represents, or fails to align with any standard
    # _boto3_response_override allows a top level key to be mapped to a new representation
    # e.g. KafkaCluster.BrokerNodeGroupInfo -> KafkaCluster.brokers
    _boto3_response_override = dict()

    def __init__(self, **kwargs):
        self._as_dict = {} if not kwargs.get('_loaded') else {k: v for k, v in kwargs.items() if k != '_loaded'}
        self.client_id = getattr(self, 'client_id', self.key_prefix)

        for response_key, new_key in self._boto3_response_override.items():
            val = kwargs.pop(response_key, None)
            if val:
                kwargs[new_key] = val

        for k, v in kwargs.items():
            self._set_attr(k, v)

    @property
    def client(self):
        return self._client.get(self.boto3_client_name)

    def _recursive_normalizer(self, obj):
        """Recursively normalizes an object.
        This is really the core logic behind everything.

        Responsibilities:
            Convert from camel case to snake case for any dict key
            Map an object to the correct class, and create an instance of that class
                Support any of the following structures:
                    dict
                    list<any>
                        If ! list<dict> resolve object var based on key:
                            LoadBalancerNames -> name is the key
                            SecurityGroups -> id is the key

        :param obj:
        :return: normalized obj
        """
        if isinstance(obj, dict):
            new = obj.__class__()
            for obj_key, obj_val in obj.items():
                obj_key = camel_to_snake(obj_key)
                if not new.get(obj_key):
                    new[obj_key] = self._recursive_normalizer(obj_val)

        elif isinstance(obj, (list, set, tuple)):
            new = obj.__class__(self._recursive_normalizer(v) for v in obj)
        else:
            return obj

        return new

    def _set_attr(self, obj_key, obj_val):
        """Normalize and set the given attribute.

        :param k:
        :param v:
        :return:
        """
        # This isn't in the recursive function to support nested objects
        #   Like a security group containing security objects
        if obj_key.startswith(self.client_id):
            obj_key = obj_key.replace(self.client_id, "")

        obj_key = camel_to_snake(obj_key)
        svc_alias = self._response_alias.get(obj_key)
        if svc_alias:
            self.create_service_field(obj_key, svc_alias)
            new_class = self._get_service_class(svc_alias)
            if isinstance(obj_val, list):
                obj_val = [new_class(**svc_instance) for svc_instance in obj_val]
            else:
                obj_val = new_class(**obj_val)
            setattr(self, obj_key, obj_val)
            return

        for svc_name in self._service_map.keys():
            if obj_key.startswith(svc_name):
                new_class = self._get_service_class(svc_name)
                orig_key = str(obj_key)
                if isinstance(obj_val, list):
                    if all(isinstance(svc_instance, dict) for svc_instance in obj_val):
                        obj_key = f'{svc_name}s'
                        obj_val = [new_class(**svc_instance) for svc_instance in obj_val]
                    else:
                        # Sketchy logic incoming
                        # If the name doesn't include the key, use id as the key.
                        # e.g. LoadBalancerNames -> name is the key
                        #       SecurityGroups -> id is the key
                        if orig_key == f'{svc_name}s':
                            cls_key = 'id'
                        else:
                            # extract the key
                            obj_key = f'{svc_name}s'
                            cls_key = orig_key.replace(svc_name, "")
                            cls_key = cls_key[1:] if cls_key.startswith("_") else cls_key
                            cls_key = cls_key[:-1] if cls_key.endswith("s") else cls_key

                        obj_val = [new_class(**{cls_key: svc_val}) for svc_val in obj_val]

                elif not isinstance(obj_val, ServiceWrapper):
                    # extract the key
                    obj_key = svc_name
                    cls_key = orig_key.replace(f"{svc_name}_", "").replace(svc_name, "")
                    obj_val = new_class(**{cls_key: obj_val})
                else:
                    return

                self.create_service_field(obj_key, svc_name)
                setattr(self, obj_key, obj_val)
                return

        normalized_output = self._recursive_normalizer({obj_key: obj_val})
        try:
            self.__setattr__(obj_key, normalized_output[obj_key])
        except AttributeError:
            AttributeError(obj_key, normalized_output[obj_key])

    def as_dict(self):
        return self._as_dict

    async def _load(self, **kwargs):
        fnc_base = camel_to_snake(self.key_prefix)
        describe_fnc = getattr(self.client, self._boto3_describe_def.get('client_call', f'describe_{fnc_base}s'))
        call_params = dict()
        for param_name, param_attrs in self._boto3_describe_def['call_params'].items():
            default_val = param_attrs.get('default')
            value = kwargs.get(param_name, getattr(self, param_name, None))

            if default_val:
                call_params[param_attrs['name']] = default_val

            if value:
                if param_attrs['type'] == list:
                    value = value if isinstance(value, list) else [value]
                    param_val = kwargs.get(param_attrs['name'], []) + value
                    call_params[param_attrs['name']] = param_val
                else:
                    call_params[param_attrs['name']] = value

        if not call_params:
            raise AttributeError(f'No valid parameters provided. {self._boto3_describe_def["call_params"].keys()}')

        response = describe_fnc(**call_params)
        response = response[self._boto3_describe_def.get('response_key', f'{self.key_prefix}s')]
        if response:
            if len(response) == 1:
                response = response[0]
                self._loaded = True
                self._as_dict = response

                # Override response attrs if they hit on an override key
                for response_key, new_key in self._boto3_response_override.items():
                    val = response.pop(response_key, None)
                    if val:
                        response[new_key] = val

                for k, v in response.items():
                    self._set_attr(k, v)
            else:
                raise ValueError('Response was not unique')

        return self

    async def load(self, **kwargs):
        """Hits the client to retrieve the entirety of the object.

        Used for returning loading the rest of an object that is generated as part of another object's response.

        Example:
        for asg_obj in aws.asg.list():
            if 'launch_configuration' in asg_obj.__dict__.keys():
                l_config = asg_obj.launch_configuration.load()
                # By calling load additional attributes like SGs are available from the launch config
                for sg in l_config.security_groups:
                    # sg's only attribute is currently id
                    sg.load()
                    # Now that sg.load is called I can reference any attribute returned by describe_security_groups
                    print(sg.name)


        :return:
        """
        force = kwargs.pop('force', False)
        if force or not self._loaded:
            self._loaded = True
            return await self._load(**kwargs)
        else:
            return self

    async def fetch(self, *args, **kwargs):
        """Given the name of an instance attribute, retrieves that related attribute from AWS

        The value of the attribute will be updated accordingly and the Service object will be returned.

        fetch/with_related was deliberately omitted from list due to one of its key features.
        The args in fetch can be nested using __ as a delimiter to pull everything you need ahead of time.
        The benefit of this is performance, and readability but operations can get expensive quick.
        Another thing to keep in mind is operations aren't lazy and joins don't exist.
        Each related object incur a lookup to AWS.

        As an example, if you wanted to inspect all ECS Service scaling policies for your production ECS clusters.
        
        # This would get all ECS clusters, filter for production clusters
        #   then retrieve the related services and the services scaling policies.
        ecs_cluster = await AWS.ecs_cluster.list()
        f = Filter(name__icontains_any=['prod-', 'production'])
        prod_clusters = await f.run(ecs_cluster)
        await prod_clusters.fetch('services__scaling_policies')

        # If this were ok, the unassuming eye would think these were the same.
        # Surprise! The number of lookups is 3n (if there were a dev and stg equivalent for each prod cluster)
        ecs_cluster = await AWS.ecs_cluster.list(with_related=['services__scaling_policies'])
        f = Filter(name__icontains_any=['prod-', 'production'])
        prod_clusters = await f.run(ecs_cluster)

        :param force: bool default False. If true, the service(s) will be re-pulled from AWS
        :param args:
        :return: Service
        """
        async def _fetch(svc_name, svc_fetch_args):
            svc_obj = getattr(self, svc_name, None)
            svc_fetch_args = [arg for arg in svc_fetch_args if arg]
            if svc_obj is None:
                # This is expected not all AWS resources have every property defined
                #   e.g. An ASG may not have an EC2 instance if desired = 0 and min = 0
                return svc_obj
            loaded_obj = await svc_obj.fetch(*svc_fetch_args, **kwargs)
            setattr(self, svc_name, loaded_obj)

        async_loads = defaultdict(list)
        custom_load_methods = []
        force = kwargs.get('force', False)

        if force or not self._loaded:
            await self.load(**kwargs)

        for arg in args:
            arg_split = arg.split('__')
            cls_attr = arg_split[0]
            attr_args = None if len(arg_split) == 1 else '__'.join(arg_split[1:])
            custom_load_method = getattr(self, f'load_{cls_attr}', None)

            if custom_load_method:
                if custom_load_method not in custom_load_methods:
                    custom_load_methods.append(custom_load_method)
                if not attr_args:
                    continue
            elif any(sub_arg.startswith(f'{arg}__') for sub_arg in args):
                continue

            async_loads[cls_attr].append(attr_args)

        # Custom load methods exist as a way to create a reference to an AWS resource that isn't returned in the client
        # An example of this would be the ASG pulls security groups from its launch config
        #   The ASG property 'accessible_resources' is generated using the security groups
        #   These properties are populated using a load_${attribute_name} method defined within the class or parent
        #   These methods are not thread safe because, in following with this example:
        #       load_accessible_resources calls load_accessible_resources which calls load_config.load
        for custom_load_method in custom_load_methods:
            await custom_load_method(force=force)

        await asyncio.gather(*[_fetch(attr_svc, attr_svc_args) for attr_svc, attr_svc_args in async_loads.items()])
        return self

    def create_service_field(self, field_name, service_class):
        """

        :param field_name: name of the attribute for the instance
        :param service_class: Name of the Service class
        :return:
        """
        if getattr(self, field_name, None) is None:
            service_class = self._get_service_class(service_class)
            setattr(type(self), field_name, ServiceWrapper(service_class, field_name))

    def fields(self):
        """The attributes for the AWS Service instances are created dynamically so this helps inspect relevant fields
        fields() will also return attributes that aren't part of the normal boto3 response but are related to the service
        An example of this would an asg's instances

        These fields can be populated in 2 different ways:
        1.) It can be passed in when initially retrieving the object using the get method like this
            asg = await AWS.asg.get(name='sample', with_related=['instances'])
        2.) Calling fetch on the instance attribute.
            asg = await AWS.asg.list()
            await asg.fetch(['instances'])

        :return:
        """
        cluster_fields = {}
        for k in dir(self):
            if not callable(getattr(self, k)) and not k.startswith('_'):
                v = getattr(self, k)
                if isinstance(v, ServiceWrapper):
                    cluster_fields[k] = re.findall("'(.*)'", str(v.service_class))[0]
                else:
                    cluster_fields[k] = re.findall("'(.*)'", str(type(v)))[0]

        return cluster_fields

    def methods(self):
        """The attributes for the AWS Service instances are created dynamically so this helps inspect relevant methods

        :return:
        """

        cluster_methods = []
        for k in dir(self):
            if callable(getattr(self, k)) \
                    and not k.startswith('_') \
                    and not k.startswith('load_') \
                    and (k != 'load' or not self._loaded) \
                    and k not in ['create_service_field', 'filter', 'get', 'list']:
                cluster_methods.append(k)

        return cluster_methods

    @classmethod
    async def get(cls, with_related=[], **kwargs) -> ServiceWrapper:
        """Hits the client to set the entirety of the object using the provided lookup field.

        :param with_related: list of related AWS resources to return
        :return:
        """
        resp = ServiceWrapper(cls)
        obj = cls(**kwargs)
        await obj.load()
        if with_related:
            await obj.fetch(*with_related)

        resp.service = obj
        return resp

    @classmethod
    async def _list(cls, **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org
        :param kwargs:
        :return: list<cls()>
        """
        fnc_base = camel_to_snake(cls.key_prefix)
        client = cls._client.get(cls.boto3_client_name)
        list_fnc = getattr(client, cls._boto3_list_def.get('client_call', f'list_{fnc_base}s'))
        describe_fnc = getattr(client, cls._boto3_describe_def.get('client_call', f'describe_{fnc_base}s'))
        list_key = cls._boto3_list_def.get('response_key', f'{cls.key_prefix}Arns')
        describe_key = cls._boto3_describe_def.get('response_key', f'{cls.key_prefix}s')
        describe_kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.pop('describe_kwargs').items()}
        list_kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.pop('list_kwargs').items()}
        results = paginated_search(list_fnc, list_kwargs, list_key)
        if not results:
            return results

        chunk_size = describe_kwargs.pop('chunk_size', 25)
        loaded_results = await describe_resource(
            describe_fnc, id_key=describe_key, id_list=results, search_kwargs=describe_kwargs, chunk_size=chunk_size
        )
        response = list(chain.from_iterable([lr.get(describe_key) for lr in loaded_results]))
        return [cls(_loaded=True, **obj) for obj in response]

    @classmethod
    async def list(cls, fnc_name=None, response_key=None, **kwargs) -> ServiceWrapper:
        """Returns an instance for each object

        :param fnc_name:
        :param response_key:
        :param kwargs:
        :return: list<cls()>
        """
        resp = ServiceWrapper(cls)
        service_list = kwargs.pop('service_list', [])

        for boto3_def, fnc_kwargs in [(cls._boto3_list_def, 'list_kwargs'),
                                      (cls._boto3_describe_def, 'describe_kwargs')]:
            boto3_params = boto3_def['call_params']
            kwargs[fnc_kwargs] = {}
            for param_name, param_attrs in boto3_params.items():
                default_val = param_attrs.get('default')
                value_list = [getattr(service, param_name, None) for service in service_list]
                value_list = [v for v in value_list if v]
                kwarg_val = kwargs.pop(param_name, [])
                value_list += kwarg_val if isinstance(kwarg_val, list) else [kwarg_val]

                if default_val:
                    kwargs[param_attrs['name']] = default_val
                    kwargs[fnc_kwargs][param_attrs['name']] = default_val

                for value in value_list:
                    if value:
                        if param_attrs['type'] == list:
                            value = value if isinstance(value, list) else [value]
                            param_val = kwargs.get(param_attrs['name'], []) + value
                            kwargs[param_attrs['name']] = param_val
                            kwargs[fnc_kwargs][param_attrs['name']] = param_val
                        else:
                            kwargs[param_attrs['name']] = value
                            kwargs[fnc_kwargs][param_attrs['name']] = value

        if fnc_name and response_key:
            kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.items()}
            client = cls._client.get(cls.boto3_client_name)
            boto3_fnc = getattr(client, fnc_name)
            response = paginated_search(boto3_fnc, kwargs, response_key)
            resp.service = [cls(_loaded=True, **obj) for obj in response]
        else:
            resp.service = await cls._list(**kwargs)

        return resp

    @classmethod
    def get_params(cls) -> list:
        resp = []
        for arg_name, arg_def in cls._boto3_describe_def['call_params'].items():
            resp.append(dict(name=arg_name, type=str(arg_def['type'])))

        return resp

    @classmethod
    def list_params(cls) -> list:
        resp = []
        for arg_name, arg_def in cls._boto3_list_def['call_params'].items():
            resp.append(dict(name=arg_name, type=str(arg_def['type'])))

        return resp


class PaginatedBaseService(BaseService):

    @classmethod
    async def _list(cls, **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org
        :param kwargs:
        :return: list<cls()>
        """
        kwargs = {cls._to_boto3_case(k): v for k, v in kwargs.items() if k not in ['list_kwargs', 'describe_kwargs']}
        response_key = cls._boto3_describe_def.get('response_key', f'{cls.key_prefix}s')
        fnc_base = camel_to_snake(cls.key_prefix)
        fnc_name = cls._boto3_describe_def.get('client_call', f'describe_{fnc_base}s')

        client = cls._client.get(cls.boto3_client_name)
        boto3_fnc = getattr(client, fnc_name)
        response = paginated_search(boto3_fnc, kwargs, response_key)
        return [cls(_loaded=True, **obj) for obj in response]

    @classmethod
    def list_params(cls) -> list:
        return cls.get_params()

