import connexion

from opera.api.openapi import encoder

DEBUG = True


def main():
    if DEBUG:
        server = "flask"
    else:
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
