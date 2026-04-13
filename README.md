# ASF Infra CAP - Contingent Approval Provider

The Contingent Approval Provider establishes a uniform method for obtaining 
Contingent Approval for technical operations in foundation projects, such as 
release votes, committee approval of a techical decision within a specific 
security scope, etc.

Approval processes can be requested through an API and can either be 
polled or have a callback URL set for asynchronous workflows.

CAP workflows are publishes in an internal pubsub stream for auditing 
purposes.
