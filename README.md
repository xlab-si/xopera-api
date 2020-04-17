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
curl localhost:8080
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
