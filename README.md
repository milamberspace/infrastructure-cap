# ASF Infra CAP - Contingent Approval Provider

[![Front-end build and publish](https://github.com/apache/infrastructure-cap/actions/workflows/frontend-build.yml/badge.svg)](https://github.com/apache/infrastructure-cap/actions/workflows/frontend-build.yml)
[![Back-end Unit Tests](https://github.com/apache/infrastructure-cap/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/apache/infrastructure-cap/actions/workflows/backend-ci.yml)


The Contingent Approval Provider establishes a uniform method for obtaining 
Contingent Approval for technical operations in foundation projects, such as 
release votes, committee approval of a techical decision within a specific 
security scope, etc.

Approval processes can be requested through an API and can either be 
polled or have a callback URL set for asynchronous workflows.

CAP workflows are publishes in an internal pubsub stream for auditing 
purposes.
