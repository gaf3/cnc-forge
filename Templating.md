# CnC Forge - Templating

- [File](#File) - Templating in files
- [Output](#Output) - Templating in `output` blocks `code`, `change`, `content`
- [Input](#Input) - Templating in `input` blocks like `field`

![templating](img/templating.jpg)

That picture pretty much sums up how templing work in the CnC Forge. Any file, any output,
hell any input, all of them use [Jinja2](https://pypi.org/project/Jinja2/) templating.

# File

Any file, unless specified otherwise with a ![preserve](Output.md#preserve) setting, is
treated like a Jinja2 template.

The README.md file in `gaf3/test-forge/README.md` is a good example:

```
# {{ craft }}
Test Forge to test the CnC Forge
```

When forging, whatever you put in the `craft` field, that value will be the title of the `README.md` file.

In addition to if/else and for loops one of the most common action I've done in
forges is [escaping](https://jinja.palletsprojects.com/en/3.1.x/templates/#escaping). This
is really useful if the code you're writing is using templates itself or something that looks
like templates with the `{{}}`.

Check out [Jinja2 Tempating](https://jinja.palletsprojects.com/en/3.1.x/templates/) for more.

# Output

Any setting in any output can also be templated from the name of a repo to create to the name of a file:

```yaml
description: An example
output:
  code:
    github:
      repo: "{{ craft }}"
    change:
      github:
        repo: gaf3/test-forge
      content:
        source: README.md
        destination: "{{ craft }}.md"
```

When forging, whatever you put in the craft field, that value will be the name of the Repo and the
name of the `README.md` file.

Check out [Output](Output.md) for more.

# Input

Even though input fields are the source of all variables for templating, you can use templating
with input fields as well.

Consider this example:

```yaml
description: An example
input:
  fields:
  - name: fruits
    options:
    - apple
    - pear
    - orange
    multi: true
    trigger: true
  - name: "{{ fruit }}_cost"
    iterate:
      fruit: fruits
```

For every fruit you select while Forging, a cost field for that fruit will be created.

Check out [Input](Input.md) for more.
