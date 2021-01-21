VERSION?=0.1.0
TILT_PORT=6738
.PHONY: up down tag untag

up:
	test -d secret || mkdir -p secret
	test -f secret/redis.json || echo '{"host": "redis.cnc-forge"}' > secret/redis.json
	test -f secret/github.json || echo '{"user": "changeme", "token": "*******"}' > secret/github.json
	kubectx docker-desktop
	tilt --port $(TILT_PORT) up

down:
	kubectx docker-desktop
	tilt down

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
