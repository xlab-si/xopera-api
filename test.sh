#!/bin/sh

set -eu

wait_for_completion() {
    while true; do
        output="$(docker-compose exec control curl --fail-with-body api:8080/status | jq -r '.[0] | .state')"
        echo "$output"
        if ! [ "$output" = "in_progress" ]; then
            break
        fi
        sleep 0.5
    done
    docker-compose exec control curl --fail-with-body api:8080/status
}

cd test/

docker-compose up --build --timeout 0 --detach --force-recreate

api_hash="$(docker-compose ps -q api)"
docker cp scaling/ "$api_hash:/tmp/"
docker-compose exec api mv /tmp/scaling/ /tmp/app/
docker-compose exec api cp -r /tmp/app/ /

# doxec --workdir /test/scaling/ zip -r ../scaling.zip .
docker-compose exec control curl --fail-with-body        api:8080/info

validation_st='{"service_template": "service.yml", "inputs": {"some_input": "this is a value"}}'
validation_csar='{"inputs": {"some_input": "this is a value"}}'
docker-compose exec control curl --fail-with-body        api:8080/validate -H "Content-Type: application/json" -d "$validation_st"
docker-compose exec control curl --fail-with-body        api:8080/validate/servicetemplate -H "Content-Type: application/json" -d "$validation_st"
docker-compose exec control curl --fail-with-body        api:8080/validate/csar -H "Content-Type: application/json" -d "$validation_csar"

docker-compose exec control curl --fail-with-body        api:8080/validate/csar -H "Content-Type: application/json" -d '{"service_template": "service.yml", "inputs": {"some_input": "this is a value"}}'

docker-compose exec control curl --fail-with-body -XPOST api:8080/deploy -H "Content-Type: application/json" -d '{"service_template": "service.yml", "inputs": {"some_input": "this is a value"}}'
wait_for_completion
docker-compose exec control curl --fail-with-body        api:8080/outputs
docker-compose exec control curl --fail-with-body        api:8080/info

docker-compose exec control curl --fail-with-body -XPOST api:8080/notify/scale_up_trigger -H "Content-Type: text/plain" -d '{"just some": "content"}'
wait_for_completion

docker-compose exec control curl --fail-with-body -XPOST api:8080/undeploy
wait_for_completion

docker-compose exec control curl --fail-with-body        api:8080/info
