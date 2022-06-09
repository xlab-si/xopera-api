#!/bin/sh

set -eu

# get opera-api executable
opera_api_executable="$1"

# function that waits for completion of operation (e.g., deploy/undeploy/notify)
wait_for_completion() {
    while true; do
        output="$(curl -s localhost:8080/status | jq -r '.[0] | .state')"
        echo "$output"
        if ! [ "$output" = "in_progress" ]; then
            break
        fi
        sleep 0.5
    done
    curl -s localhost:8080/status
}

# perform integration test with opera-api executable
# run xOpera API in the background and save process id
$opera_api_executable > /dev/null 2>&1 &
opera_api_pid=$!
sleep 3

# prepare request body
service_template_body='{"service_template": "service.yaml", "inputs": {}}'

# test different API endpoints
curl -s localhost:8080/version
curl -s localhost:8080/info
curl -s localhost:8080/validate -H "Content-Type: application/json" -d "$service_template_body"
curl -s -XPOST localhost:8080/deploy -H "Content-Type: application/json" -d "$service_template_body"
wait_for_completion
curl -s localhost:8080/status
curl -s localhost:8080/outputs
curl -s localhost:8080/info
curl -s -XPOST localhost:8080/undeploy
wait_for_completion
curl -s localhost:8080/info
curl -s localhost:8080/status

# kill opera-api
kill $opera_api_pid
