import boto3

from nab3.base import BaseAWS, ClientHandler


class AWS(BaseAWS):

    def __init__(self, session: boto3.Session = boto3.Session()):
        client_handler = ClientHandler(session)
        self.client = client_handler
        self._get_service_classs()

    def _get_service_classs(self):
        for service_name in self._service_map.keys():
            new_class = self._get_service_class(service_name)
            self.__setattr__(service_name, new_class)
