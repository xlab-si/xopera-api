# xOpera API
An HTTP API interface to the `opera` orchestrator - single user, single project, single deployment.

[![cicd](https://github.com/xlab-si/xopera-api/actions/workflows/ci_cd.yaml/badge.svg)](https://github.com/xlab-si/xopera-api/actions/workflows/ci_cd.yaml)
[![PyPI](https://img.shields.io/pypi/v/opera-api)](https://pypi.org/project/opera-api/)
[![Test PyPI](https://img.shields.io/badge/test%20pypi-dev%20version-blueviolet)](https://test.pypi.org/project/opera-api/)

## Table of Contents
  - [Introduction](#introduction)
  - [Prerequisites](#prerequisites)
  - [Installation and Quickstart](#installation-and-quickstart)
  - [Development](#development)
  - [Usage](#usage)
  - [License](#license)
  - [Contact](#contact)
  - [Acknowledgement](#acknowledgement)

## Introduction
`opera-api` aims to be a lightweight xOpera orchestrator API. 
The [xOpera documentation] is available on GitHub pages. 

The xOpera API is not a pure orchestration service REST API and cannot deploy multiple projects from different
users. 
It is just a wrapper around user's current orchestration environment, where he has his files and his version 
of [opera] orchestrator and can manage just one state at a time. 
The reason behind this implementation is that this API does not have to support multiuser experience and is mean to be 
the component that integrates into xOpera SaaS API in the way that for each user's project a new separated Docker 
container with xOpera API is created, which can ensure that users' orchestration environments are isolated. 
[xOpera SaaS] is then the component that brings multiuser and multitenant experience by using xOpera API that mimics 
CLI commands, which is nicer than calling xOpera CLI.

## Prerequisites
`opera-api` requires Python 3 and a virtual environment. 
In a typical modern Linux environment, we should already be set. 
In Ubuntu, however, we might need to run the following commands:

```console
$ sudo apt update
$ sudo apt install -y python3-venv python3-wheel python-wheel-common
```

## Installation and Quickstart
The xOpera API is available on PyPI as a Python package named [opera-api]. 
Apart from the latest [PyPI production] version, you can also find the latest opera-api [PyPI development] version, 
which includes pre-releases so that you will be able to test the latest features before they are officially released.

The simplest way to test `opera-api` is to install it into Python virtual environment:

```console
$ python3 -m venv .venv && . .venv/bin/activate
(.venv) $ pip install opera-api
```

After that you can navigate to the folder with your TOSCA CSAR or service template and run the API that will create the
wrapper around your environment.

```console
(.venv) $ git clone git@github.com:xlab-si/xopera-api.git
(.venv) $ cd xopera-api/tests/integration/hello-world
(.venv) $ opera-api
2022-04-04 12:45:34,097 - INFO - opera.api.cli - Running in production mode: tornado backend.
```

Now open another terminal window and deploy the example through some API endpoints using `curl`:

```console
(.venv) $ (.venv) $ curl -XPOST localhost:8080/deploy -H "Content-Type: application/json" -d '{"service_template": "service.yaml", "inputs": {}}'
{
  "clean_state": false,
  "id": "a3e64611-01e0-417a-9b08-87b08b73883c",
  "inputs": {},
  "operation": "deploy",
  "service_template": "service.yaml",
  "state": "pending",
  "timestamp": "2022-04-04T10:47:49.919002+00:00"
}
(.venv) $ curl localhost:8080/info
{
  "content_root": ".",
  "csar_valid": true,
  "inputs": {},
  "service_template": "service.yaml",
  "service_template_metadata": {
    "template_author": "XLAB",
    "template_name": "hello-world",
    "template_version": "1.0"
  },
  "status": "deployed"
}
(.venv) $ curl localhost:8080/status
...
```

And that's it. 

You can also run xOpera API in a Docker container (using public [ghcr.io/xlab-si/xopera-api] Docker image) and mount 
your TOSCA CSAR:

```console
# run xOpera API in Docker and navigate to localhost:8080/swagger
$ docker run --name xopera-api -p 8080:8080 -v $(pwd)/tests/integration/hello-world:/hello-world -e OPERA_API_DEBUG_MODE=true ghcr.io/xlab-si/xopera-api
$ curl localhost:8080/status
```

If you wish to deploy another project navigate to its folder and run another instance of xOpera API. 
If you want to use `opera` orchestrator (with xOpera CLI) go to [xopera-opera] repository. 
If you want to use just xOpera TOSCA parser go to [xopera-tosca-parser] repository. 
For xOpera examples navigate to [xopera-examples] repository. 
You can also take a look at the [xOpera SaaS] component, which is designed for business partners and enterprise users. 
To find more about xOpera project visit our [xOpera documentation].

## Development
Requires Python >= 3.7.

To begin:

```console
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenAPI base code is generated with `generate.sh` and is _not_ checked in to the repository.

Other useful commands:

```console
# openapi-generator basics
java -jar openapi-generator-cli-4.3.0.jar
java -jar openapi-generator-cli-4.3.0.jar help generate
java -jar openapi-generator-cli-4.3.0.jar validate --input-spec openapi-spec.yml --recommend
java -jar openapi-generator-cli-4.3.0.jar config-help --generator-name python-flask --full-details
```

## Usage
Use xOpera API with Docker:

```console
docker-compose up --build -d
docker cp test.csar xopera-api_api_1:/app/
docker exec xopera-api_api_1 unzip test.csar
docker logs -f xopera-api_api_1
# prepare request inputs: service_template, inputs (in JSON object form, not a string)
curl -XPOST localhost:8080/validate -H "Content-Type: application/json" -d @inputs-request.json
curl -XPOST localhost:8080/deploy -H "Content-Type: application/json" -d @inputs-request.json
curl localhost:8080/status
curl localhost:8080/outputs
curl localhost:8080/info
curl -XPOST localhost:8080/undeploy
```

With a local development installation:

```console
./generate.sh
python3 -m venv .venv
source .venv/bin/activate
pip install wheel
pip install -r requirements.txt
cd src/
python3 -m opera.api.cli
curl localhost:8080
```

You can also run in debug mode and use other env vars:

```console
(.venv) $ git clone git@github.com:xlab-si/xopera-api.git
(.venv) $ cd xopera-api/tests/integration/hello-world
(.venv) $ OPERA_API_DEBUG_MODE=true OPERA_API_PORT=8000 OPERA_API_SWAGGER_URL=docs opera-api
2022-06-09 12:18:33,658 - INFO - opera.api.cli - Running in debug mode: flask backend.
 * Serving Flask app 'opera.api.cli' (lazy loading)
 ...
(.venv) $ curl localhost:8000/version
"0.6.9"
```

## License
This work is licensed under the [Apache License 2.0].

## Contact
You can contact the xOpera team by sending an email to [xopera@xlab.si].

## Acknowledgement
This project has received funding from the European Union’s Horizon 2020 research and innovation programme under Grant 
Agreements No. 825040 ([RADON]), No. 825480 ([SODALITE]) and No. 101000162 ([PIACERE]).

[xOpera documentation]: https://xlab-si.github.io/xopera-docs/
[opera]: https://pypi.org/project/opera/
[PyPI production]: https://pypi.org/project/opera-api/#history
[PyPI development]: https://test.pypi.org/project/opera-api/#history
[xopera-api]: https://github.com/xlab-si/xopera-api
[ghcr.io/xlab-si/xopera-api]: https://github.com/xlab-si/xopera-api/pkgs/container/xopera-api
[xopera-opera]: https://github.com/xlab-si/xopera-opera
[xopera-tosca-parser]: https://github.com/xlab-si/xopera-tosca-parser
[xopera-examples]: https://github.com/xlab-si/xopera-examples
[xOpera SaaS]: https://xlab-si.github.io/xopera-docs/04-saas.html
[Apache License 2.0]: https://www.apache.org/licenses/LICENSE-2.0
[xopera@xlab.si]: mailto:xopera@xlab.si
[RADON]: http://radon-h2020.eu
[SODALITE]: http://www.sodalite.eu/
[PIACERE]: https://www.piacere-project.eu/
