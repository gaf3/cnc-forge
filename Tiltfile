docker_build('cnc-forge-api', './api')
docker_build('cnc-forge-daemon', './daemon')
docker_build('cnc-forge-gui', './gui')
docker_build('cnc-forge-options', './options')

k8s_yaml(kustomize('kubernetes/tilt'))

local_resource(
    name='secret',
    cmd='kubectl --context docker-desktop -n cnc-forge create secret generic secret --from-file secret/ --dry-run=client -o yaml | kubectl --context docker-desktop apply -f -'
)

local_resource(
    name='forge', deps=["forge/"],
    cmd='kubectl --context docker-desktop -n cnc-forge create configmap forge --from-file forge/ --dry-run=client -o yaml | kubectl --context docker-desktop apply -f -'
)

k8s_resource('redis', port_forwards=['26770:5678'])


k8s_resource('api', port_forwards=['16770:80', '16738:5678'], resource_deps=['redis'])

k8s_resource('daemon', port_forwards=['26738:5678'], resource_deps=['redis'])

k8s_resource('gui', port_forwards=['6770:80'], resource_deps=['api'])

k8s_resource('options', port_forwards=['36770:80', '36738:5678'])
