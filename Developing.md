# CnC Forge - Developing

Developing Forges can be kind of tricky. There's many ways to do things but I've
found a few that work well for me.

Make sure you've followed [Local Setup](Setup.md#Local) instructions before proceeding.

# Repos

Currently, I have a Repo per item I want to forge. In that Repo I have a `forge/` directory
where I keep all the forges for that item. Like for a service, I have a forge that'll create
the service from scratch. That'll create the service's repo, and like a Database in a cloud,
and have it deploy to a cluster based on a branch.

Then I'll have a forge for that service to be in an environment, like dev or prod, which'll
have the same code as before, but only create the database and deployment to a cluster.

Then I'll have a forge that'll just deploy that service, to cluster.

But in all cases, use what works for you.

# Branching

Like any good doobie, when working on a forge Repo, I'll have a branch. With that branch, I
can copy the forges YAML to a local copy of CnC Forge's `forge/` directory. Then I can pull
code from the branch of my forge repo and test locally.

Check out [GitHub Developing](GitHub.md#Developing) for more.

# Trying

Key to testing locally is the Try action. What this does is create all the files it would commit
but doesn't. If you go the `cnc/` directory while running locally, all forged files stay there.
There's a directory the same as the `id` and for each code block, there will be a code-#
directory.

# Updating

To save you a ton of frustration, let's have a quick talk about Kubernetes and Tilt. One of the
benefits of Tilt is if you change something it'll automatically reload. HOWEVER, the timing
varies. If you change a forge in the `forge/` directory, it's safeest to go into Tilt, refresh
(click the little circle icon) the API and then the GUI once the API is back up.
