# cnc-forge

Code and Changes Forge

# yaml

All output values are transformed as Jinja2 template using the values of inputs

Current format:

```yaml
description: # Describes the Forge
input: # What to input to the Forge
  fields: # Fields to get input from (OpenGUI)
  generate: # Method to add fields or append to
output: # The Code and Changes to craft.
  code: # Repo or PR to create
  - github: # Block to describe how to interact with github
      repo: # Repo to pull
      branch: # Branch to pull
    change: # Change to code
    - github: # Block to describe how to interact with github
        repo: # Repo to use or create
        branch: # Branch to create with, set to default branch to skip a PR, default is cnc id
        pull_request: # PR to create, default to branch name
      content: # What to bring from change into code
      - source: # From directory or file
        destination: # To directory or file
        exclude: # Exclude glob pattern
        include: # Override exclude glob pattern
        preserve: # Don't transform with Jinja2 templating glob pattern
        transform: # Override transform glob pattern
        condition: # Condition to satisfy
      condition: # Condition to satisfy
    condition: # Condition to satisfy
  condition: # Condition to satisfy
```

Eventual format

```yaml
description: # Describes the Forge
input: # What to input to the Forge
  extra: # Extra common/calculated fields to use
  fields: # Fields to get input from (OpenGUI)
  - *: Standard OpenGUI attributes
    name: code - craft first two letters to ASCII port (to prevent local collisions)
    name: port - Will default to craft dashes replaced with underscores
    name: ticket - Ticket to use in making branch
    description: Description for the field
    labels: labels to use with options
    requires: Other fields that must exist
    condition: Condition to satisfy for field
output: # The Code and Changes to craft.
  code: # Repo or PR to create from
  - github: # Block to describe how to interact with github
      repo: # Repo to pull
      branch: # Branch to pull
    change: # Change to code
    - github: # Block to describe how to interact with github
        repo: # Repo to use or create
        branch: # Branch to create with, set to default branch to skip a PR, default is cnc id
        pull_request: # PR to create, default to branch name
      content: # What to bring from change into code
      - source: # From directory or file
        destination: # To directory or file
        exclude: # Exclude glob pattern
        include: # Override exclude glob pattern
        preserve: # Don't transform with Jinja2 templating glob pattern
        transform: # Override preserve glob pattern
        transpose: # Set new values with old
        condition: # Condition to satisfy
        iterate: # Iterate from a list variable into a new variable
      condition: # Condition to satisfy
      iterate: # Iterate from a list variable into a new variable
    condition: # Condition to satisfy
    iterate: # Iterate from a list variable into a new variable
  condition: # Condition to satisfy
  iterate: # Iterate from a list variable into a new variable
```

API lookup

```yaml
- name: dynamic
  description: JIRA ticket associated with the task
  api:
    uri: $ Url endpoint to hit
    params: # What to put in the query string
      name: value
    body: # what to put in the JSON body
    options: # Key in the return body that referances array, if blank will use whole body as array
    option: # Key in each array element to use as option value
    title: # Key in each array element to use as title value (optional)
    auth: # Secrets separate
      username: # What to use for basic auth
        secret: # Name of secret to use
      password: # What to use for basic auth
        secret: # Name of secret to use
    auth: # Secrets together
      secret: # Name of secret to use (username and password fields)
    token: # What to use for bearer token
      secret: # Name of secret to use
    headers: # Extra headers to send
      name: value
      name:
        secret: # Name of secret to use
```

Secret can also be

```yaml
secret:
  name: # The name of the secret
  path: # Path to the secret in dot/arrya format
```

Else it'll just grab the whole secret as the value

Some experiental ideas

```
iterate:
  one: many
  one: many

source: .vscode/gui.launch.json
destination: .vscode/.launch.json
json:
  append: configurations because the

source: .vscode/python.launch.json
destination: .vscode/.launch.json
transpose:
  python: daemon
json:
  append: configurations

source: image.Jenkinsfile
destination: Jenkinsfile
transpose:
  microservice: api
text:
  inject: image

source: cleanup.Jenkinsfile
destination: Jenkinsfile
transpose:
  microservice: api
text:
  inject: cleanup
```
