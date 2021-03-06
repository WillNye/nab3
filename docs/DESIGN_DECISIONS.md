# Design Decisions

## Objectives
The primary purposes of nab3 are as followed:
* Standardizing output 
* Standardizing accessors
* Simplifying access patterns
* Creating an interface between services to make it possible to traverse a service and its relationships

## Design Considerations
In addition to that, the following considerations needed to be made for nab3 to be viable
* Multiple AWS Sessions must be supported, e.g. a user should be able to list all ASGs in USE1 and EUC1 within the script.
* Must be async to minimize bottleneck for reporting scripts and/or fetching downstream services on a large response
* Designed in such a way to prevent users from implicitly shooting themselves in the foot
* Maintain client connections in some capacity to prevent spamming new client connections and inadvertent mem leaks

## Why is it called the `Service` class and not `Resource` class?
In boto3 they're referred to as a service so this helps maintain consistency.
Plus, come on. It's called Amazon Web Services not Amazon Web Resources.

## Why does nab3 only support read operations?
There are a few reasons why, at this time, nab3 is read only.

First, I only have so much time.
Reads take less development time because parsing the AWS response doesn't need to be validated with the same scrutiny 
and have a smaller impact if something goes wrong.

Second, due to dependencies and using dependency output when provisioning AWS resources you probably shouldn't try to make provisioning operations async.

Third, I'm a huge fan of python but everything has it's place. 
If you're attempting to automate resource provisioning or want infrastructure represented in code you should really check out [Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs). 

### What if I still want to use it to help with creating, updating, or destroying a service?
nab3 is a low level wrapper and exposes the service client via the `service.client` property so this is still possible.

As an example, here is how you could use nab3 to delete all services within an ECS cluster:

```python
import asyncio

from double_click import echo

from nab3 import AWS as NabAWS

AWS = NabAWS()
CLUSTER = asyncio.run(AWS.ecs_cluster.get(name='example', with_related=['services']))

for service in CLUSTER.services:
    echo(f'### Destroying {CLUSTER.name} - {service.name}')
    resp = service.client.delete_service(cluster=CLUSTER.name, service=service.name, force=False)
```


