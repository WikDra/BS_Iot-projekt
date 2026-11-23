
import datetime as dt

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash

from . import __version__
from .auth import create_access_token, jwt_required
from .validation import ValidationError, validate_measurement

bp = Blueprint("api", __name__, url_prefix="/api")


def _now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


@bp.get("/status")
def status():
    store = current_app.extensions["iot_store"]
    return jsonify(
        status="ok",
        service="iot-api",
        version=__version__,
        server_time=_now_iso(),
        measurements_stored=len(store),
    )


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        current_app.logger.warning("Odrzucono logowanie: wymagany obiekt JSON")
        return jsonify(error="Request body must be a JSON object"), 400

    username = data.get("username")
    password = data.get("password")
    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not username
        or not password
    ):
        current_app.logger.warning("Odrzucono logowanie: brak lub błędny typ loginu i hasła")
        return jsonify(error="Fields 'username' and 'password' are required"), 400

    # Sprawdzamy hash także przy błędnym loginie, żeby nie zdradzać go czasem odpowiedzi.
    password_ok = check_password_hash(current_app.config["IOT_PASSWORD_HASH"], password)
    if username != current_app.config["IOT_USERNAME"] or not password_ok:
        current_app.logger.warning("Nieudane logowanie użytkownika %r", username)
        return jsonify(error="Invalid username or password"), 401

    expires_in = current_app.config["JWT_EXPIRES_SECONDS"]
    token = create_access_token(
        username=username,
        secret=current_app.config["JWT_SECRET_KEY"],
        expires_in=expires_in,
    )
    g.username = username
    current_app.logger.info("Zalogowano użytkownika %r", username)
    return jsonify(access_token=token, token_type="Bearer", expires_in=expires_in)


@bp.get("/measurements")
@jwt_required
def get_measurements():
    measurements = current_app.extensions["iot_store"].get_all()
    return jsonify(measurements)


@bp.get("/measurements/stats")
@jwt_required
def get_measurement_stats():
    measurements = current_app.extensions["iot_store"].get_all()
    result: dict[str, object] = {"count": len(measurements)}
    for field in ("temperature", "humidity"):
        values = [measurement[field] for measurement in measurements if field in measurement]
        if values:
            result[field] = {
                "min": min(values),
                "max": max(values),
                "avg": round(sum(values) / len(values), 2),
            }
        else:
            result[field] = None
    return jsonify(result)


@bp.post("/measurements")
@jwt_required
def add_measurement():
    try:
        measurement = validate_measurement(request.get_json(silent=True))
    except ValidationError as exc:
        current_app.logger.warning("Odrzucono pomiar: %s", exc)
        return jsonify(error=str(exc)), 400

    measurement["received_at"] = _now_iso()
    record = current_app.extensions["iot_store"].add(measurement)
    current_app.logger.info(
        "Pomiar #%d device_id=%r: %.2f °C", record["id"], record["device_id"], record["temperature"]
    )
    return jsonify(record), 201
