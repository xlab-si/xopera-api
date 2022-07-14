import os
import shutil
import connexion
from opera.api.log import get_logger
from opera.api.openapi import encoder

DEBUG = os.getenv("OPERA_API_DEBUG_MODE", "false") == "true"
WORKDIR = os.getenv("OPERA_API_WORKDIR", None)
logger = get_logger(__name__)


def main():
    try:
        if DEBUG:
            logger.info("Running in debug mode: flask backend.")
            server = "flask"
        else:
            logger.info("Running in production mode: tornado backend.")
            server = "tornado"

        app = connexion.App(__name__, specification_dir="./openapi/openapi/", server=server, options=dict(
            serve_spec=DEBUG,
            swagger_ui=DEBUG,
            swagger_url=os.getenv("OPERA_API_SWAGGER_URL", "swagger")
        ))

        if WORKDIR:
            try:
                shutil.copytree(WORKDIR, os.getcwd(), dirs_exist_ok=True)
            except OSError as e:
                print(f"Cannot copy files from working directory {WORKDIR}, exception: {str(e)}")

        app.app.json_encoder = encoder.JSONEncoder
        app.add_api("openapi.yaml", arguments={"title": "xOpera API"}, pythonic_params=True)
        app.run(port=int(os.getenv("OPERA_API_PORT", 8080)), debug=DEBUG)
    except Exception as e:
        print(f"Exception: {str(e)}")


if __name__ == "__main__":
    main()
