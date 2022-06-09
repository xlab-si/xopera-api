#!/bin/sh

set -eu

# function that waits for completion of operation (e.g., deploy/undeploy/notify)
wait_for_completion() {
    while true; do
        output="$(docker-compose exec control curl -s --fail-with-body api:8080/status | jq -r '.[0] | .state')"
        echo "$output"
        if ! [ "$output" = "in_progress" ]; then
            break
        fi
        sleep 0.5
    done
    docker-compose exec control curl -s --fail-with-body api:8080/status
}

# set up Docker containers
docker-compose up --build --timeout 0 --detach --force-recreate

# prepare and copy example files
api_hash="$(docker-compose ps -q api)"
docker cp ../integration/scaling/ "$api_hash:/tmp/"
docker-compose exec api mv /tmp/scaling/ /tmp/app/
docker-compose exec api cp -r /tmp/app/ /

# prepare request body
service_template_body='{"service_template": "service.yaml", "inputs": {"some_input": "this is a value"}}'

# test different API endpoints
docker-compose exec control curl -s --fail-with-body        api:8080/version
docker-compose exec control curl -s --fail-with-body        api:8080/info
docker-compose exec control curl -s --fail-with-body        api:8080/validate -H "Content-Type: application/json" -d "$service_template_body"
docker-compose exec control curl -s --fail-with-body -XPOST api:8080/deploy -H "Content-Type: application/json" -d "$service_template_body"
wait_for_completion
docker-compose exec control curl -s --fail-with-body        api:8080/outputs
docker-compose exec control curl -s --fail-with-body        api:8080/info
docker-compose exec control curl -s --fail-with-body -XPOST api:8080/notify/scale_up_trigger -H "Content-Type: text/plain" -d '{"just some": "content"}'
wait_for_completion
docker-compose exec control curl -s --fail-with-body -XPOST api:8080/undeploy
wait_for_completion
docker-compose exec control curl -s --fail-with-body        api:8080/info
