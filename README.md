# xOpera API

An HTTP API interface to the `opera` orchestrator.
Mimics CLI commands.

WIP.

## Development

To begin:

```shell script
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenAPI base code is generated with `generate.sh` and is _not_ checked in to the repository.

Other useful commands:

```shell script
# openapi-generator basics
java -jar openapi-generator-cli-4.3.0.jar
java -jar openapi-generator-cli-4.3.0.jar help generate
java -jar openapi-generator-cli-4.3.0.jar validate --input-spec openapi-spec.yml --recommend
java -jar openapi-generator-cli-4.3.0.jar config-help --generator-name python-flask --full-details
```

## Usage

With Docker:

```shell script
docker-compose up --build
docker cp test.csar xopera-api_api_1:/app/
docker exec xopera-api_api_1 unzip test.csar
# prepare request inputs: service_template, inputs (in JSON object form, not a string)
curl -XPOST localhost:8080/validate -H "Content-Type: application/json" -d @inputs-request.json
curl -XPOST localhost:8080/deploy -H "Content-Type: application/json" -d @inputs-request.json
curl localhost:8080/status
curl localhost:8080/outputs
curl -XPOST localhost:8080/undeploy
```

With a local development installation:

```shell script
./generate.sh
python3 -m venv .venv
source .venv/bin/activate
pip install wheel
pip install -r requirements.txt
cd src/
python3 -m opera.api.cli
curl localhost:8080
```

## Building for PyPI, releases

* Generate sources with `./generate.sh`.
* Test built packages in a Docker container.
* Only release tags without any local changes present.
* Manually create and upload releases onto GitHub, no automation for that.
* Build and test before pushing tags to reduce rollbacks.

```bash
pip3 install -r requirements.txt
./generate.sh
git tag -a 1.2.3 -m 1.2.3

rm -rfv dist/
python setup.py sdist bdist_wheel

docker run -it --rm -v $(realpath ./dist/):/dist/:ro python:3.8-buster bash
    pip3 install dist/*.whl
    opera-api
    pip3 uninstall -y opera-api
    pip3 install dist/*.tar.gz
    opera-api

twine upload --repository <pypi|testpypi> dist/*
# upload to github manually

git push --tags
```
