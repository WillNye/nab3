import sys

import boto3

from nab3.utils import camel_to_snake


class ClientHandler:

    def __init__(self, session: boto3.Session = boto3.Session()):
        self._session = session

    def get(self, service_name):
        """Retrieves the client resource object.
        Clients are set using the object's session lazily.

        :param service_name:
        :return:
        """
        service = getattr(self, service_name, None)
        if not service:
            service = self._session.client(service_name)
            setattr(self, service_name, service)
        return service


class BaseAWS:
    _client: ClientHandler
    loaded_service_classes = {}
    _service_map = dict(
        alarm='Alarm',
        asg='ASG',
        scaling_policy='AutoScalePolicy',
        launch_configuration='LaunchConfiguration',
        security_group='SecurityGroup'
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
    client_name: str
    key_prefix: str
    """_service_list_map maps each element in the list to a service class.
    This is an effort to ensure proper mapping on nested objects.
        example: describe_security_groups contains UserIdGroupPairs
            Each element is essentially a security group with some extra metadata
    """
    _service_list_map = {}

    def __init__(self, **kwargs):
        key_prefix = getattr(self, 'key_prefix', None)
        if not key_prefix:
            self.key_prefix = self.client_name

        for k, v in kwargs.items():
            self._set_attr(k, v)

    @property
    def client(self):
        return self._client.get(self.boto3_service_name)

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

    def load(self):
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
        raise NotImplementedError

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
    def list(cls, search_fnc: str = None, search_str: str = "") -> list:
        """Returns an instance for each object
        JMESPath for filtering: https://jmespath.org

        :param search_str: str passed to paginate().search.
        :param search_fnc: The client call to be ran
        :return: list<cls()>
        """
        client = cls._client.get(cls.boto3_service_name)
        client_name = f"{cls.client_name}s"
        search_fnc = search_fnc if search_fnc else f'describe_{camel_to_snake(client_name)}'
        paginator = client.get_paginator(search_fnc)
        page_iterator = paginator.paginate(PaginationConfig={'PageSize': 100})
        query = f'{client_name}[]' if not search_str else search_str
        filtered_response = page_iterator.search(query)
        resp = [cls(**result) for result in filtered_response]
        return resp
