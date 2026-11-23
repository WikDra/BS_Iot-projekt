
import datetime as dt
import math
import re

DEVICE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
TEMPERATURE_RANGE = (-50.0, 100.0)
HUMIDITY_RANGE = (0.0, 100.0)


class ValidationError(ValueError):
    pass


def _number(data, field, value_range, required):
    if field not in data:
        if required:
            raise ValidationError(f"Field '{field}' is required")
        return None
    value = data[field]
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (isinstance(value, float) and not math.isfinite(value))
    ):
        raise ValidationError(f"Field '{field}' must be a number")
    low, high = value_range
    if not low <= value <= high:
        raise ValidationError(f"Field '{field}' must be between {low} and {high}")
    return float(value)


def validate_measurement(data):

    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    device_id = data.get("device_id")
    if not isinstance(device_id, str) or not DEVICE_ID_RE.fullmatch(device_id):
        raise ValidationError(
            "Field 'device_id' must be 1-64 characters: letters, digits, '-' or '_'"
        )

    clean = {
        "device_id": device_id,
        "temperature": _number(data, "temperature", TEMPERATURE_RANGE, required=True),
    }

    humidity = _number(data, "humidity", HUMIDITY_RANGE, required=False)
    if humidity is not None:
        clean["humidity"] = humidity

    if "timestamp" in data:
        timestamp = data["timestamp"]
        try:
            parsed = dt.datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            raise ValidationError("Field 'timestamp' must be an ISO 8601 date-time") from None
        clean["timestamp"] = parsed.isoformat()

    return clean
