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
  fields: # Fields to get input from (OpenGUI)
  generate: # Method to add fields or append to
  validate: # Method to call to validate fields
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
        transform: # Override transform glob pattern
        condition: # Condition to satisfy
        iterate: # Iterate from a list variable into a new variable
        generate: # Generate changes with a function
      condition: # Condition to satisfy
      iterate: # Iterate from a list variable into a new variable
      generate: # Generate changes with a function
    condition: # Condition to satisfy
    iterate: # Iterate from a list variable into a new variable
    generate: # Generate changes with a function
  condition: # Condition to satisfy
  iterate: # Iterate from a list variable into a new variable
  generate: # Generate changes with a function
```

Some experiental ideas

```
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
