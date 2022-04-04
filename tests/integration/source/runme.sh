#!/bin/sh

set -eu

# get opera-api executable
opera_api_executable="$1"

# perform integration test with opera-api executable
cd hello-world
# run xOpera API in the background and save process id
$opera_api_executable > /dev/null 2>&1 &
opera_api_pid=$!
sleep 3

# test different API endpoints
curl localhost:8080/info
curl localhost:8080/validate/servicetemplate -H "Content-Type: application/json" -d '{"service_template": "service.yaml", "inputs": {}}'
curl localhost:8080/validate/csar -H "Content-Type: application/json" -d '{"service_template": "service.yaml", "inputs": {}}'
curl -XPOST localhost:8080/deploy -H "Content-Type: application/json" -d '{"service_template": "service.yaml", "inputs": {}}'
curl localhost:8080/status
curl localhost:8080/outputs
curl localhost:8080/info
curl -XPOST localhost:8080/undeploy
curl localhost:8080/info
curl localhost:8080/status

# kill opera-api
kill $opera_api_pid
