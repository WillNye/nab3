# nab3, how it works and why

## nab3.BaseAWS
nab3 is centered around the BaseAWS class. It is the foundation for the AWS class and all Service classes.
It allows you to interface with the service classes defined within nab3 using its lazy loaded boto3 clients.
The boto3 session and clients are contained within the attribute `BaseAWS._client_handler`. 
This is a super important point that I'll explain shortly. 

### BaseAWS._get_service_class
This method will be the unsung hero of nab3 and is the linchpin of nab3's design. 

When a service is accessed either using the AWS class or another service it doesn't create an instance of the service class but an instance of the class returned from the _get_service_class call.
I know what you're thinking, "isn't that the same thing".

Well yes, but actually no. Remember that super important point? 
The client handler instance is a class attribute not an instance attribute. 
This is how the get and list Service methods are feasible. 
Example: `ecs_cluster.list()` returns a wrapper class containing a list of ECSCluster instances along with helper methods

Because N different client connections are supported concurrently, nab3 relies on the Service class to determine which client connection is used.
Since the class determines the client the client handler should be an attribute of the class itself. 
  
The problem is, the scope of the client handler attribute should not extend outside of the AWS instance it was created under.
Otherwise one AWS instance would implicitly change the client handler attributes of another AWS instance.
In other words, if you set the class attribute but you have multiple sessions, you're gonna have a bad time.

To accommodate this issue, a new class type is created and referenced that is unique to the AWS instance.
This is where `BaseAWS._get_service_class` comes in.
It will get or create a type that is identical to the provided service class with the following naming structure `f'{service_class}x{str(id(self._service_map))}'`.
The client handler for that class will set to what is essentially a pointer to the AWS instance's client handler.

## nab3.AWS
If you've seen the implementation you'll notice there's not a lot going on. It's legit only 8 lines of code.
The class is really only an "entrypoint" for users with a helper method to list the services supported by nab3 and ties a `ClientHandler` instance to an object. 

If you're familiar with sqlalchemy the tldr is:
* `nab3.AWS` == `sqlalchemy.orm.sessionmaker`
* `boto3.Session` == `sqlalchemy.create_engine`
BUT with the added complexity of maintaining n different lazy loaded boto3 clients.
>If you're not familiar with sqlalchemy this was probably not a helpful tldr.

## nab3.base.ServiceWrapper
If you're familiar with Django, its purpose is similar to QuerySet.
When a query like `User.objects.all()` is returned in Django to get all users, the type isn't `list`, or `User` but `QuerySet`.

The reason for this in nab3 is likely the same as it is in Django. The purpose is to standardize the object response and allow for helper methods.
For example, the method `fetch` in nab3 will retrieve the service(s) related to one or more instances of a service class as illustrated here:
```python
from nab3 import AWS as NabAWS

AWS = NabAWS()
ASG = await AWS.asg.list()
await ASG.fetch('instances')
``` 
Without a wrapper class, you'd be trying to call fetch on a list which is obviously not a supported method.

It also serves purposes like:
* Attribute validation when it is being set
* Standardizing service class operations like checking if all services are loaded
* copy method to prevent implicit pointers 

## nab3.base.BaseService
The BaseService inherits BaseAWS and provides the methods to interface with boto3 and a default implementation.

The boto3 accessor methods are:
* load
* list
* fetch

`get` just calls load behind the scenes.
Each of these methods use the attributes outlined in the [contribution doc](CONTRIBUTING.md) to generate a request that is then normalized by `_recursive_normalizer` on init.

In addition to the boto3 accessors, BaseService provides helper methods to inspect the service object.

The methods are (which do exactly what it sounds like they do):
* fields
* methods

