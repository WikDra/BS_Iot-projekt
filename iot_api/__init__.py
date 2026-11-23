import os
import secrets

from flask import Flask
from werkzeug.security import generate_password_hash

from .storage import MeasurementStore

__version__ = "0.1.0"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        JWT_SECRET_KEY=os.environ.get("IOT_JWT_SECRET"),

        JWT_EXPIRES_SECONDS=int(os.environ.get("IOT_JWT_EXPIRES", "900")),
        IOT_USERNAME=os.environ.get("IOT_USERNAME", "admin"),
        IOT_PASSWORD=os.environ.get("IOT_PASSWORD"),
        MAX_STORED_MEASUREMENTS=1000,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    if not app.config["JWT_SECRET_KEY"]:
        app.config["JWT_SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning(
            "IOT_JWT_SECRET nie jest ustawiony - wylosowano klucz; "
            "tokeny przestaną być ważne po restarcie serwera"
        )
    if len(app.config["JWT_SECRET_KEY"]) < 32:
        raise RuntimeError("IOT_JWT_SECRET musi mieć co najmniej 32 znaki")

    password = app.config.pop("IOT_PASSWORD", None)
    if not password:
        raise RuntimeError(
            "Ustaw zmienną środowiskową IOT_PASSWORD (hasło użytkownika API)"
        )

    app.config["IOT_PASSWORD_HASH"] = generate_password_hash(password)
    app.extensions["iot_store"] = MeasurementStore(app.config["MAX_STORED_MEASUREMENTS"])

    from .routes import bp

    app.register_blueprint(bp)

    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    @app.errorhandler(500)
    def handle_http_error(error):
        response = error.get_response()
        response.set_data(app.json.dumps({"error": error.name}))
        response.content_type = "application/json"
        return response

    return app
