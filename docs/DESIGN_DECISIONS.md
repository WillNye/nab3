## Why does nab3 only support read operations?
There are a few reasons why, at this time, nab3 is read only.

First, I only have so much time.
Reads take less development time because parsing the AWS response doesn't need to be validated with the same scrutiny 
and have a smaller impact if something goes wrong.

Second, due to dependencies and using dependency output when provisioning AWS resources you probably shouldn't try to make provisioning operations async.

Third, I'm a huge fan of python but everything has it's place. 
If you're attempting to automate resource provisioning or want infrastructure represented in code you should really check out [Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs). 


