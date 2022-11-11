ACCOUNT=gaf3
IMAGE=cnc-forge-gui
VERSION?=0.7.0
NAME=$(IMAGE)-$(ACCOUNT)

.PHONY: cross build shell push install update remove reset

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . --build-arg BASE=$(BASE) -t $(ACCOUNT)/$(IMAGE):$(VERSION)

shell:
	-docker run -it --rm $(ACCOUNT)/$(IMAGE):$(VERSION) sh

push:
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)

install:
	kubectl create -f kubernetes/gui.yaml

update:
	kubectl replace -f kubernetes/gui.yaml

remove:
	-kubectl delete -f kubernetes/gui.yaml

reset: remove install
