import boto3

from nab3.base import BaseAWS, ClientHandler


class AWS(BaseAWS):

    def __init__(self, session: boto3.Session = boto3.Session()):
        self._client = ClientHandler(session)

    def __getattr__(self, value):
        if value in self._service_map.keys():
            return self._get_service_class(value)
        return getattr(self, value)

    def service_options(self):
        """
        Returns a list of supported service classes
        :return:
        """
        return sorted([k for k in self._service_map.keys()])
