import os

import connexion

from opera.api.openapi import encoder
from opera.api.log import get_logger

DEBUG = os.getenv("DEBUG", "false") == "true"
logger = get_logger(__name__)


def main():
    if DEBUG:
        logger.info("Running in debug mode: flask backend.")
        server = "flask"
    else:
        logger.info("Running in production mode: tornado backend.")
        server = "tornado"

    app = connexion.App(__name__, specification_dir="./openapi/openapi/", server=server, options=dict(
        serve_spec=False,
        swagger_ui=False
    ))
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api("openapi.yaml", arguments={"title": "xOpera API"}, pythonic_params=True)
    app.run(port=8080, debug=DEBUG)


if __name__ == "__main__":
    main()
