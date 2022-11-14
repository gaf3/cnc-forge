# cnc-forge - github

CnC Forge is currently setup to use GitHub to source code and create code.

Right now GitHub the code repository git/API CnC Forge uses but I made everything modular
and just haven't got around to creating a module for like GitLab or BitBucket, etc.

# setup

The CnC Forge uses one secret in the `cnc-forge` Kubernetes namespace, esoterically called `secret`.

The CnC Forge interacts with GitHub two ways. First, it uses the GitHub API to query and create Repos
and Pull Requests. Second, it uses git and SSH Keys to check out and commit code.

All GitHub creds files are prefixed with `github_`, and each set of creds requires two files. First,
all the information it needs to interact with the account on a GitHub server. Second, and an SSH
private key to checkout and commit code.

## accounts

For each GitHub account you're using make sure you have:
- A [GitHub](https://github.com/) account that can create Repos and Pull Requests
- A [GitHub Personal Access Token](https://github.com/settings/tokens) that can create Repos and Pull Requests
- A [GitHub SSH Key Pair](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) without a password with the public key added to the GitHub account.

Wait, isn't that last step dangerous? Oh yes. I'm looking to harden that up but don't ever share what's generated above.

## default

To create a default set of creds, credit a file called `github_default.json` like so:

```json
{
    "user": "your GitHub username",
    "token": "your GitHub Personal Access Token",
    "url": "the base api url for the api (optional - default https://api.github.com)",
    "host": "the host to use for checkouts and commits (optional - default github.com)"
}
```

And a file of the SSH private key called `github_default.key`. Put both in the secret for CnC Forge.

Whether the CnC Forge sees a `github` YAML block, it'll use these creds by default.

## account

To create a set of creds for a different account, do everything you did for for `default`, pick a name like
`other` and simply name the files `github_other.json` and `github_other.key` and put them in the same secret.

Whether the CnC Forge sees a `github.creds: other` setting in a `github` YAML block, it'll use these creds.

# usage

The `github` blocks are used in blocks `code` and `change`. But there are some setting that universal to both.

## universal

### creds

(optional) The creds files to use. Default is, well, `default`.

### repo

This is like the name of the repo but more shorthand.

If there's a `/` in the value, it's assume the org is proceeding the `/`.

If there's no `/` in the value, it's assumed the repo belongs to the user in teh creds.

This field is never used by processing. It's used to figure our fields like `name`, `path`, etc.

### name

(optional) The actual name of the repo. You don't have to set this if you used `repo`.

### org

(optional) The actual org of the repo. You don't have to set this if you used `repo` with a `/`.

### user

(optional) The actual org of the repo. You don't have to set this if you used `repo` without a `/`.

### path

(optional) This is the path used to communicate with the API. You don't have to set this if you used `repo`.

## code

In a `code` block, a `github` block tells the CnC Forge how to create a Pull Request (and a Repo if it doesn't
exist). It can have the following additional fields.

### prefix

(optional - but I always use it) This field is used to add some extra info to all the work the CnC
Forge is doing.

When set, this field is added to the branch name for the Pull Request (when not set, the CNC id is use)
And not by coincidence, the branch is also used as the title of the Pull Request by default.

### branch

(optional) This field is used to name the branch of the Pull Request. If not set, it'll be `{{ prefix }}-{{ id }}`
if `prefix` is set and just `id` if `prefix` is not.

### title

(optional) This field is used to title the Pull Request. If not set, it'll be whatever the `branch` is.

### base

(optional) This is the branch to use as the base branchof the Pull Request. If not set it'll use the
Repo's default branch.

### hook

(optional) - Webhook(s) to ensure on the Repo. This is useful for CICD (which is what I used the CnC Forge all
the time).

It's pretty flexible. It can be a str, a dict, or list of str/dict.

As a string, it's assume to be a dict with url as the string value. As a non list, it's assumed to be a list.

Thus:

```yaml
github:
  hook: http://trigger.com
```

Is equivalent to:

```yaml
github:
  hook:
  - url: http://trigger.com
```

Whatever is in that dict is sent to the GitHub API as `config`, so you can add fields based on the
[API Documentation](https://docs.github.com/en/rest/webhooks/repos#create-a-repository-webhook)

Note: This is done only during the "Commit" action. "Try" doesn't do anything with it.

### comment

(optional) - Comments(s) to enter on the Pull Request. This is useful for any GitOps Automation that
can be pre-approved.

It's pretty flexible. It can be a str, a dict, or list of str/dict.

As a string, it's assume to be a dict with body as the string value. As a non list, it's assumed to be a list.

Thus:

```yaml
github:
  comment: /approve
```

Is equivalent to:

```yaml
github:
  comment:
  - body: /approve
```

Whatever is in that dict is sent to the GitHub API as teh payload, so you can add fields based on the
[API Documentation](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment)

Note: This is done only during the "Commit" action. "Try" doesn't do anything with it.

## change

In a `change` block, a `github` block tells the CnC Forge how to grab code to make changes. So it has addtional
fields, but not as many as `code` and they don't do as much.

### branch

If you want to grab code from a different branch than the Repo's default branch, use this field to
specify the branch.
