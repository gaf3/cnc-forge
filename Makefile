VERSION?=0.4.1
TILT_PORT=6738
.PHONY: up down tag untag

up:
	mkdir -p cnc
	mkdir -p forge
	mkdir -p secret
	echo "- op: replace\n  path: /spec/template/spec/volumes/0/hostPath/path\n  value: $(PWD)/cnc" > kubernetes/tilt/cnc.yaml
	tilt --port $(TILT_PORT) up --context docker-desktop

down:
	tilt down --context docker-desktop

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
