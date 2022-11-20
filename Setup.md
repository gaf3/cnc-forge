# CnC Forge - Setup

The CnC Forge is a web service made to run in Kubernetes.

- [Local](#Local) - Get CnC Forge running on your computer
- [Production](#Production) - Get CnC Forge running in Production (someone else's computer)

Make sure you have:
- A [GitHub](https://github.com/) account that can create Repos and Pull Requests
- A [GitHub Personal Access Token](https://github.com/settings/tokens) that can create Repos and Pull Requests
- A [GitHub SSH Key Pair](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) without a password with the public key added to the GitHub account.

Wait, isn't that last step dangerous? Oh yes. I'm looking to harden that up but don't ever share what's generated above.

# Local

This is how to run the CnC Forge locally.

I've only tested this on a Mac but it should work with Linux, if with a little finangling. Windows? Um, good luck everyone!

Make sure you have installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Kustomize](https://kustomize.io/)
- [Tilt](https://docs.tilt.dev/install.html)

Setup:
- Check out this repo.
- Create a `secret/` directory (which is .gitignore'd)
- Copy your ssh private key to `secret/github_default.key`
- Create a `secret/github_default.json` file:

```json
{
    "user": "your GitHub username",
    "token": "your GitHub Personal Access Token"
}
```

Running:
- At a bash prompt type `make up`
- Hit space when prompted to open Tilt in a browser
- If any services shows up red, just click the reload circular arrow next to them until green.
- When the GUI service turns green, click on it.
- Look for a localhost link and click on that to enter CnC Forge running locally on your machine.

Forges:
- Just put any forges in `forges/` which was automatically created with `make up`
- It takes few minutes to propagate to the local CnC Forge.
- Updating forges also takes a bit to propagate.

You can speed up the propagation in Tilt by refreshing the API and then the GUI.

Stopping:
- Hit Ctrl-C where you typed `make up`
- Type `make down`

# Production

This is how to deploy the CnC Forge to a production environment where I'm assuming you have a good
understanding of Kubernetes and Kustomize and are down with IasC (ya you know me).

The CnC Fotge consists of 3 microservices, api, daemon, gui, and a Redis instance. Each has a directory in this Repo with
a `kubernetes\base` directory inside that.

In your IasC repo:

Setup:
- Create a `cnc-forge` directory (or whatever you want, this name doesn't matter)
- Create a `forge/` inside that (this name very much matters) and put your forges within, ie `service.yaml`
- Create a `secret/` inside that and fill it with same GitHub files from Local above
- Create a `kustomization.yaml` next to `forge/`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: cnc-forge
resources:
- github.com/gaf3/cnc-forge/redis/kubernetes/base/?ref=64f0df412ff86ed8c6c6227e8f539a15e4baacb0
- github.com/gaf3/cnc-forge/api/kubernetes/base/?ref=64f0df412ff86ed8c6c6227e8f539a15e4baacb0
- github.com/gaf3/cnc-forge/gui/kubernetes/base/?ref=64f0df412ff86ed8c6c6227e8f539a15e4baacb0
- github.com/gaf3/cnc-forge/daemon/kubernetes/base/?ref=64f0df412ff86ed8c6c6227e8f539a15e4baacb0
configMapGenerator:
- name: forge
  files:
  - forge/service.yaml
```

Replace `64f0df412ff86ed8c6c6227e8f539a15e4baacb0` with whatever commit hash you want to run (the Repo has tags) and add
any all the forges within `forge/` to the configMapGenerator.

Deploying:
- Make sure you're pointing to the right cluster...
- Type `kubectl create namespace cnc-forge` to create the namespace
- Type `kubectl -n cnc-forge create secret generic secret --from-file secret/` to create the secret
- Type `kubectl apply -k .` to deploy the CnC Forge

NOTE: Make sure you don't commit what's in `secret/`! Also, you probably want to be using some sort of secrets
manager. Just make sure the secret ends up in the pattern above.
