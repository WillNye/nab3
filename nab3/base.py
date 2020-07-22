import asyncio
import copy
import sys
from itertools import chain
from collections import defaultdict

import boto3
import botocore

from nab3.utils import camel_to_snake, describe_resource, Filter, paginated_search, snake_to_camelback


class ClientHandler:
    """Maintains state of N different boto3 client connections
    """

    def __init__(self, session: boto3.Session = boto3.Session(),
                 default_config: botocore.client.Config = botocore.client.Config(max_pool_connections=10)):
        self._botocore_config = default_config
        self._session = session

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
        instance='EC2Instance',
        launch_configuration='LaunchConfiguration',
        load_balancer='LoadBalancer',
        load_balancer_classic='LoadBalancerClassic',
        metric='Metric',
        scaling_policy='AutoScalePolicy',
        security_group='SecurityGroup',
    )

    @property
    def client(self):
        return self._client

    def _get_service_class(self, service_name):
        service_class = self._service_map[service_name]
        class_ref = getattr(sys.modules['nab3.service'], service_class)
        class_name = f'{service_class}x{str(id(self._service_map))}'
        loaded_service = self.loaded_service_classes.get(class_name)
        if loaded_service:
            return loaded_service

        new_class = type(
            class_name,
            class_ref.__bases__,
            dict(class_ref.__dict__)
        )
        self.loaded_service_classes[class_name] = new_class
        new_class._client = self._client

        return new_class


class BaseService(BaseAWS):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """
    boto3_service_name: str
    client_id: str
    key_prefix: str
    """_response_alias maps each element in the list to a service class.
    This is an effort to ensure proper mapping on nested objects.
        example: describe_security_groups contains UserIdGroupPairs
            Each element is essentially a security group with some extra metadata
    """
    _loaded = False
    _response_alias = {}
    # These are in relation to the call within the boto3 client
    # Not all clients/resources have a list operation
    _boto3_describe_def = dict(
        # client_call: str default f'describe_{camel_to_snake(self.client_id)}s'
        # response_key: str default f'{self.client_id}s'
        call_params=dict(),  # variable_name: str = dict(name:str, type:any)
    )
    _boto3_list_def = dict(
        # client_call: str default f'list_{camel_to_snake(self.client_id)}s'
        # response_key: str default f'{self.client_id}Arns'
        call_params=dict(),  # variable_name: str = dict(name:str, type:any)
    )

    def __init__(self, **kwargs):
        key_prefix = getattr(self, 'key_prefix', None)
        if not key_prefix:
            self.key_prefix = self.client_id

        for k, v in kwargs.items():
            self._set_attr(k, v)

    @property
    def client(self):
        return self._client.get(self.boto3_service_name)

    @property
    def loaded(self):
        return self._loaded

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
        if obj_key.startswith(self.key_prefix):
            obj_key = obj_key.replace(self.key_prefix, "")

        obj_key = camel_to_snake(obj_key)
        svc_list_alias = self._response_alias.get(obj_key)
        if svc_list_alias:
            self.create_service_field(obj_key, svc_list_alias)
            setattr(self, obj_key, obj_val)
            return

        for svc_name in self._service_map.keys():
            if obj_key.startswith(svc_name):
                new_class = self._get_service_class(svc_name)
                orig_key = str(obj_key)
                if isinstance(obj_val, list):
                    if all(isinstance(svc_instance, dict) for svc_instance in obj_val):
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

                elif not isinstance(obj_val, ServiceDescriptor):
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

    def create_service_field(self, field_name, service_class):
        if getattr(self, field_name, None) is None:
            service_class = self._get_service_class(service_class)
            setattr(type(self), field_name, ServiceDescriptor(service_class, field_name))

    async def _load(self, **kwargs):
        fnc_base = camel_to_snake(self.client_id)
        describe_fnc = getattr(self.client, self._boto3_describe_def.get('client_call', f'describe_{fnc_base}s'))
        call_params = dict()
        for param_name, param_attrs in self._boto3_describe_def['call_params'].items():
            value = kwargs.get(param_name, getattr(self, param_name, None))
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
        response = response[self._boto3_describe_def.get('response_key', f'{self.client_id}s')]
        if response:
            if len(response) == 1:
                for k, v in response[0].items():
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
        if not self.loaded:
            self._loaded = True
            return await self._load(**kwargs)
        else:
            return self

    async def fetch(self, *args):
        async def _fetch(svc_name, svc_fetch_args):
            svc_obj = getattr(self, svc_name, None)
            svc_fetch_args = [arg for arg in svc_fetch_args if arg]
            if not svc_obj:
                # This is expected not all AWS resources have every property defined
                #   e.g. An ASG may not have an EC2 instance if desired = 0 and min = 0
                return svc_obj

            if svc_fetch_args:
                loaded_obj = await svc_obj.fetch(*svc_fetch_args)
            else:
                loaded_obj = await svc_obj.load()

            setattr(self, svc_name, loaded_obj)

        async_loads = defaultdict(list)
        custom_load_methods = []

        if not self.loaded:
            await self.load()

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
            await custom_load_method()

        await asyncio.gather(*[_fetch(attr_svc, attr_svc_args) for attr_svc, attr_svc_args in async_loads.items()])

        return self

    @classmethod
    async def get(cls, with_related=[], **kwargs):
        """Hits the client to set the entirety of the object using the provided lookup field.

        :param with_related: list of related AWS resources to return
        :return:
        """
        obj = cls(**kwargs)
        await obj.load()
        if with_related:
            await obj.fetch(*with_related)
        return obj

    @classmethod
    async def _list(cls, **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org
        :param kwargs:
        :return: list<cls()>
        """
        fnc_base = camel_to_snake(cls.client_id)
        client = cls._client.get(cls.boto3_service_name)
        list_fnc = getattr(client, cls._boto3_list_def.get('client_call', f'list_{fnc_base}s'))
        describe_fnc = getattr(client, cls._boto3_describe_def.get('client_call', f'describe_{fnc_base}s'))
        list_key = cls._boto3_list_def.get('response_key', f'{cls.client_id}Arns')
        describe_key = cls._boto3_describe_def.get('response_key', f'{cls.client_id}s')
        describe_kwargs = {snake_to_camelback(k): v for k, v in kwargs.pop('describe_kwargs').items()}
        list_kwargs = {snake_to_camelback(k): v for k, v in kwargs.pop('list_kwargs').items()}
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
    async def list(cls, fnc_name=None, response_key=None, **kwargs) -> list:
        """Returns an instance for each object

        :param fnc_name:
        :param response_key:
        :param kwargs:
        :return: list<cls()>
        """
        service_list = kwargs.pop('service_list', [])

        for boto3_def, fnc_kwargs in [(cls._boto3_list_def, 'list_kwargs'),
                                      (cls._boto3_describe_def, 'describe_kwargs')]:
            boto3_params = boto3_def['call_params']
            kwargs[fnc_kwargs] = {}
            for param_name, param_attrs in boto3_params.items():
                value_list = [getattr(service, param_name, None) for service in service_list]
                value_list = [v for v in value_list if v]
                kwarg_val = kwargs.get(param_name, [])
                value_list += kwarg_val if isinstance(kwarg_val, list) else [kwarg_val]

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
            kwargs = {snake_to_camelback(k): v for k, v in kwargs.items()}
            client = cls._client.get(cls.boto3_service_name)
            boto3_fnc = getattr(client, fnc_name)
            response = paginated_search(boto3_fnc, kwargs, response_key)
            return [cls(_loaded=True, **obj) for obj in response]

        return await cls._list(**kwargs)

    @classmethod
    async def filter(cls, **kwargs) -> list:
        """Returns an instance for each object

        :param kwargs:
        :return: list<cls()>
        """
        filter_operations = [f'__{filter_op}' for filter_op in Filter.get_operations()]
        filter_kwargs = {k: v for k, v in kwargs.items() if any(k.endswith(op) for op in filter_operations)}
        kwargs = {k: v for k, v in kwargs.items() if k not in filter_kwargs.keys()}
        service_objects = await cls.list(**kwargs)
        if service_objects and filter_kwargs:
            filter_obj = Filter(**filter_kwargs)
            return await filter_obj.run(service_objects)
        else:
            return service_objects


class PaginatedBaseService(BaseService):

    @classmethod
    async def _list(cls, **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org
        :param kwargs:
        :return: list<cls()>
        """
        kwargs = {snake_to_camelback(k): v for k, v in kwargs.pop('describe_kwargs', {}).items()}
        response_key = cls._boto3_describe_def.get('response_key', f'{cls.client_id}s')
        fnc_base = camel_to_snake(cls.client_id)
        fnc_name = cls._boto3_describe_def.get('client_call', f'describe_{fnc_base}s')

        client = cls._client.get(cls.boto3_service_name)
        boto3_fnc = getattr(client, fnc_name)
        response = paginated_search(boto3_fnc, kwargs, response_key)
        return [cls(_loaded=True, **obj) for obj in response]


class ServiceDescriptor:

    def __init__(self, service_class: BaseService, name: str):
        self._name = name
        self.service_class = service_class
        self.service = None

    def is_loaded(self):
        if self.service is None:
            return False
        elif self._is_list():
            return all(svc.loaded for svc in self.service)
        else:
            return self.service.loaded

    def _is_list(self) -> bool:
        return isinstance(self.service, list)

    async def load(self):
        if self.service:
            if self._is_list() and not self.is_loaded():
                self.service = await self.service_class.list(service_list=self.service)
            elif not self.is_loaded():
                await self.service.load()
        return self.service

    async def fetch(self, *args):
        if self.service:
            if self._is_list():
                await asyncio.gather(*[svc.fetch(*args) for svc in self.service])
            else:
                await self.service.fetch(*args)
        return self.service

    def __set__(self, obj, value) -> None:
        if isinstance(value, ServiceDescriptor):
            value = value.service

        if isinstance(value, list) and all(isinstance(elem_val, self.service_class) for elem_val in value):
            self.service = value
        elif not isinstance(value, list) and isinstance(value, self.service_class):
            self.service = value
        else:
            raise ValueError(f'{value} != (list<{self.service_class}> || {self.service_class})')

    def __getattr__(self, value):
        if value is 'loaded':
            return self.is_loaded()
        elif value is 'load':
            return self.load
        elif self.service is None:
            return getattr(self.service_class, value, None)
        return getattr(self.service, value, None)

    def __iter__(self):
        if isinstance(self.service, list):
            yield from self.service
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

