# cnc-forge - input

The optional `input` section of a forge defines what fields and how they all work.

- [fields](#fields) - Field settings
  - [name](#name) - What to call the field and how to reference in templating
  - [required](#required) - Make a field required
  - [validation](#validation) - How to validation a field with a regex
  - [trigger](#trigger) - Make the form reload if a field changes
  - [default](#default) - Default value for a field
  - [readonly](#readonly) - Make a field for display only
  - [description](#description) - Describe what the field does
  - [link](#link) - Add a helpful link or two
  - [options](#options) - Only allow certain values via radio buttons
  - [titles](#titles) - Give those only values their own descriptions
  - [multi](#multi) - Allow to select multiple options with checkboxes
  - [bool](#bool) - Have a value be only true or false with a single checkbox
  - [style](#style) - Change the appearance of text or options
    - [textarea](#textarea) - Make a regular text field a textarea field
    - [select](#select) - Put option in a drop down
    - [optional](#optional) - Have that drop down have a blank option
  - [field.fields](#field.fields) - Fields with their own sub fields
  - [requires](#requires) - Require other fields to have values before considering this one
  - [templating](#templating) - Using field values in another's settings.
  - [condition](#condition) - Display this field conditionally
  - [iterate](#iterate) - Create multiple field based on another's selections
  - [blocks](#blocks) - Group several fields for a single condition/iterate
- [builtin](#builtin) - Fields that are added to every forge
  - [forge](#forge) - Forge selected
  - [craft](#craft) - What you're forging
  - [additional](#additional) - Additional builtins to add to all forges
  - [update](#update) - Updating a builtin field with different settings
  - [override](#override) - Overriding the craft field with your own

# fields

Fields are defined in the `input.fields` section. For example if you wanted a text field
named example, you'd define it like so:

## name

```yaml
description: An example
input:
  fields:
  - name: example
```

It would display:

![name](/img/name.png)

Filling it in:

![name-demo](/img/name-demo.png)

It would be evaluated for processing as:

```json
{
    "example": "demo"
}
```

And you could reference it in your code:

```
This is the {{ example }} example.
```

Which would be rendered:

```
This is the demo example.
```

## required

If a field must have a value, add a required:

```yaml
description: An example
input:
  fields:
  - name: example
    required: true
```

Which indicates missing values:

![required](/img/required.png)

## validation

If a field needs to match a regex, you can add validation:

```yaml
description: An example
input:
  fields:
  - name: example
    validation: ^[a-z]{3,6}$
```

The CnC Forge will let the user know if invalid:

![validation](/img/validation.png)

## trigger

If you're using required or validation, you should have that field trigger

```yaml
description: An example
input:
  fields:
  - name: example
    validation: ^[a-z]{3,6}$
    trigger: true
```

When the user changes that field, the field values will be sent to API and re-validated, updating the page
if the issue has been fixed.

This isn't required, the same validation check will be performed when you try to Commit, but it does make for
a better user experience.

## default

You can add a default:

```yaml
description: An example
input:
  fields:
  - name: example
    default: sure
```

And it starts off with that value:

![default](/img/default.png)

## readonly

If you want a value force you can use readonly with default like so:

```yaml
description: An example
input:
  fields:
  - name: example
    default: sure
    readonly: true
```

And it stays with that value:

![readonly](/img/readonly.png)

The forge value at the top works this way.

## description

You can add a description to a field and it will appear in italics under the field.

```yaml
description: An example
input:
  fields:
  - name: example
    description: This is an example
```

It would display:

![description](/img/description.png)

## link

You can add a link or two to a field and it will appear under the field.

This can be as simple a just a url:

```yaml
description: An example
input:
  fields:
  - name: example
    link: https://github.com/gaf3/cnc-forge
```

Which displays:

![link](/img/link.png)

Or it can be an array of links, with the name to display even target to open in (defaults to _b;ank):

```yaml
description: An example
input:
  fields:
  - name: example
    link:
    - url: https://github.com/gaf3/cnc-forge
      name: CnC Forge
      target: codin
    - https://pypi.org/project/yaes/
```

Which displays:

![links](/img/links.png)

## options

You can add options to a field  as a list to limit selections:

```yaml
description: An example
input:
  fields:
  - name: example
    options:
    - 1
    - 2
    - 3
```

It would display:

![options](/img/options.png)

And be evaluated as:

```json
{
    "example": 2
}
```

You can also pull options from an API. Check out [Options](/Options.md)

## titles

You can add titles to options to change what the user sees when forging:

```yaml
description: An example
input:
  fields:
  - name: example
    options:
    - 1
    - 2
    - 3
    titles:
      1: One
      2: Two
      3: Three
```

Which would display differently:

![titles](/img/titles.png)

But evaluate the same:

```json
{
    "example": 2
}
```

You can also pull titles from an API with options. Check out [Options](/Options.md)

## multi

You can turn those options to checkboxes and allow for multiple values:

```yaml
description: An example
input:
  fields:
  - multi: true
    name: example
    options:
    - 1
    - 2
    - 3
```

Which would display:

![multi](/img/multi.png)

And evaluate as an array:

```json
{
    "example": [2, 3]
}
```

## bool

If you need something as simple as a checkbox, use the bool flag:

```yaml
description: An example
input:
  fields:
  - name: example
    bool: true
```

Which displays as:

![bool](/img/bool.png)

And always evaluates as true or false:

```json
{
    "example": false
}
```

## style

You can alter the appearance of a few different types of fields with style.

### textarea

If you want a regular text field to become a textarea:

```yaml
description: An example
input:
  fields:
  - name: example
    style: textarea
```

Which displays as:

![textarea](/img/textarea.png)

### select

If you want options to appear in select element:

```yaml
description: An example
input:
  fields:
  - name: example
    options:
    - 1
    - 2
    - 3
    style: select
```

Which displays as:

![select](/img/select.png)

### optional

If you have options with a select style, you can also make the field optional:

```yaml
description: An example
input:
  fields:
  - name: example
    options:
    - 1
    - 2
    - 3
    style: select
    optional: true
```

Which displays as:

![optional](/img/optional.png)

Note the empty option.

## field.fields

Fields can have fields!

```yaml
description: An example
input:
  fields:
  - name: example
    fields:
    - name: more
    - name: fun
```

Which display as:

![field](/img/field.png)

And are evaluated accordingly:

```json
{
    "example": {
        "more": "yes",
        "fun": "please"
    }
}
```

## requires

We can have fields depend on the values of other fields. But before we can do that, we
have to make sure the fields we're going to use have values. Say we wanted to have our
example field use the fruits field. We'd specify that example requires fruits.

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
  - name: example
    requires: fruits
```

Nothing to display here, but see below how it works.

## templating

With the dependecies listed, we can use Jinja2 templating in all field settings.

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
  - name: example
    requires: fruits
    description: "describe these {{ fruits | length }} fruits"
```

And when we select fruits, the description is updated accordingly:

![templating](/img/templating.png)

This use of templating works in any field setting allow for some crazy dynamic behavior.

## condition

If you want to only show a field based on another, use a condition

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
  - name: example
    condition: "{? 'apple' in fruits ?}"
    requires: fruits
```

If apple is not selected, example doesn't show:

![condition-false](/img/condition-false.png)

When apply is selected, example does show:

![condition-true](/img/condition-true.png)

## iterate

You can also use field to create other fields through iteration:

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

Selecting no fruits shows no costs:

![iterate-none](/img/iterate-none.png)

Selecting some fruits shows matching costs:

![iterate-some](/img/iterate-some.png)

## blocks

If you want to apply conditions or iteration to more than one field you can group
them with blocks and those blocks can even have conditions and iteration:

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
  - iterate:
      fruit: fruits
    requires: fruits
    blocks:
    - name: "{{ fruit }}_cost"
    - name: "{{ fruit }}_price"
    - name: "{{ fruit }}_shine"
      bool: true
      condition: "{? fruit != 'orange' ?}"
```

Selecting no fruits shows no fields:

![blocks-none](/img/blocks-none.png)

Selecting some fruits shows matching fields:

![blocks-some](/img/blocks-some.png)

# builtin

There are two fields built in: `forge` and `craft`.

## forge

The forge field just stores what forge you pick. It's used to generate the id.

This is what it's YAML looks like:

```yaml
name: forge
description: what to craft from
readonly: true
```

## craft

The craft field is what you're calling this run. Usually it's used for the name of a repo or a file.

This is what it's YAML looks like:

```yaml
name: forge
description: craft
validation: ^[a-z][a-z0-9\-]{1,46}$
required: true
triggered: true
```

## additional

You can add your own built in fields to CnC Forge deployment. Add a `fields.yaml` to the `forge/`
Directory/ConfigMap.

Here's one I always have:

```yaml
fields:
- name: ticket
  description: JIRA ticket associated with the task
  default: YOLO-420
  valid: "^[A-Z]+-[0-9}+"
```

Which displays as:

![additional](/img/additionalpng)

All fields specified in `fields.yaml` will appear in every forge after the `forge` and `craft` fields.

## update

You can update any field by adding another field with the same name. This will taken whatever settings
you specify and update the dictionary of settings for the field with the same name:

```yaml
description: An example
input:
  fields:
  - name: craft
    description: She's crafty and just my type
```

Which displays as:

![update](/img/update.png)

## override

You can also completely override the `input.craft` field entirely with a different field like so:

```yaml
description: An example
input:
  craft: example
  fields:
  - name: example
```

Which displays as:

![override](/img/override)

The override field will be used in the id, just like the craft field typically is. If the override
field is multi, it'll use the first selected value. If there's no values, everything will just fail.
