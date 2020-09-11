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

Well yes, but actually no. Remember that super important point? When all 



## nab3.AWS
If you've seen the implementation you'll notice there's not a lot going on. It's legit only 8 lines of code.
The class is really only an "entrypoint" for users with a helper method to list the services supported by nab3 and ties a `ClientHandler` instance to an object. 

If you're familiar with sqlalchemy the tldr is:
* `nab3.AWS` == `sqlalchemy.orm.sessionmaker`
* `boto3.Session` == `sqlalchemy.create_engine`
BUT with the added complexity of maintaining n different lazy loaded boto3 clients.
>If you're not familiar with sqlalchemy this was probably not a helpful tldr.

## nab3.base.ServiceDescriptor

## nab3.base.BaseService & nab3.base.PaginatedBaseService

