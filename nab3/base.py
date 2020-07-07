import asyncio
import copy
import sys
from itertools import chain

import boto3
import botocore

from nab3.utils import async_describe, camel_to_snake, paginated_search, snake_to_camelback


class ClientHandler:

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
    """_service_list_map maps each element in the list to a service class.
    This is an effort to ensure proper mapping on nested objects.
        example: describe_security_groups contains UserIdGroupPairs
            Each element is essentially a security group with some extra metadata
    """
    _loaded = False
    _service_list_map = {}

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
                svc_list_alias = self._service_list_map.get(obj_key)
                if svc_list_alias:
                    new_class = self._get_service_class(svc_list_alias)
                    if not any(isinstance(svc_instance, new_class) for svc_instance in obj_val):
                        # Prevents logic errors in recursive call
                        obj_val = [new_class(**svc_instance) for svc_instance in obj_val]
                    new[obj_key] = obj_val
                    continue

                for svc_name in self._service_map.keys():
                    if obj_key.startswith(svc_name):
                        new_class = self._get_service_class(svc_name)
                        if isinstance(obj_val, new_class) or \
                                (isinstance(obj_val, list)
                                 and any(isinstance(svc_instance, new_class) for svc_instance in obj_val)):
                            # Prevents logic errors in recursive call
                            new[obj_key] = obj_val
                            break

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
                                    obj_key = svc_name
                                    cls_key = orig_key.replace(svc_name, "")
                                    cls_key = cls_key[1:] if cls_key.startswith("_") else cls_key
                                    cls_key = cls_key[:-1] if cls_key.endswith("s") else cls_key
                                obj_val = [new_class(**{cls_key: svc_val}) for svc_val in obj_val]
                        elif not isinstance(obj_val, new_class):
                            # extract the key
                            obj_key = svc_name
                            cls_key = orig_key.replace(f"{svc_name}_", "").replace(svc_name, "")
                            obj_val = new_class(**{cls_key: obj_val})
                        break

                new[obj_key] = self._recursive_normalizer(obj_val)

        elif isinstance(obj, (list, set, tuple)):
            new = obj.__class__(self._recursive_normalizer(v) for v in obj)
        else:
            return obj

        return new

    def _set_attr(self, k, v):
        """Normalize and set the given attribute.

        :param k:
        :param v:
        :return:
        """
        # This isn't in the recursive function to support nested objects
        #   Like a security group containing security objects
        if k.startswith(self.key_prefix):
            k = k.replace(self.key_prefix, "")

        normalized_output = self._recursive_normalizer(self._recursive_normalizer({k: v}))
        for new_k, new_v in normalized_output.items():
            attr_key = new_k
            attr_val = new_v
            break

        self.__setattr__(attr_key, attr_val)

    def _load(self, **kwargs):
        raise NotImplementedError

    def load(self, **kwargs):
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
            return self._load(**kwargs)
        else:
            return self

    @classmethod
    def get(cls, name):
        """Hits the client to set the entirety of the object using the provided lookup field.

        Default filter field is normally name

        :param name:
        :return:
        """
        obj = cls(name=name)
        obj.load()
        return obj

    @classmethod
    def _list(cls,
              list_fnc=None,
              describe_fnc=None,
              list_key: str = None,
              describe_key: str = None,
              describe_kwargs: dict = {},
              loop=asyncio.get_event_loop(),
              **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org

        :param loop: Optionally pass an event loop
        :param kwargs:
        :return: list<cls()>
        """
        if list_fnc is None or describe_fnc is None:
            fnc_base = camel_to_snake(cls.client_id)
            client = cls._client.get(cls.boto3_service_name)

            if list_fnc is None:
                list_fnc = getattr(client, f'list_{fnc_base}s')
            if describe_fnc is None:
                describe_fnc = getattr(client, f'describe_{fnc_base}s')

        list_key = list_key if list_key else f'{cls.client_id}Arns'
        describe_key = describe_key if describe_key else f'{cls.client_id}s'
        describe_kwargs = {snake_to_camelback(k): v for k, v in describe_kwargs.items()}
        search_kwargs = {snake_to_camelback(k): v for k, v in kwargs.items()}
        results = paginated_search(list_fnc, search_kwargs, list_key)
        loaded_results = async_describe(describe_fnc,
                                        id_key=describe_key,
                                        id_list=results,
                                        loop=loop,
                                        search_kwargs=describe_kwargs,
                                        chunk_size=describe_kwargs.pop('chunk_size', 5))
        response = list(chain.from_iterable([lr.get(describe_key) for lr in loaded_results]))
        return [cls(_loaded=True, **obj) for obj in response]

    @classmethod
    def list(cls, loop=asyncio.get_event_loop(), **kwargs) -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org

        :param loop: Optionally pass an event loop
        :param kwargs:
        :return: list<cls()>
        """
        return cls._list(loop, **kwargs)
