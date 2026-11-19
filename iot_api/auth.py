from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, jsonify, request


def create_access_token(username, secret, expires_in=900):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def jwt_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "").split()
        if len(authorization) != 2 or authorization[0].lower() != "bearer":
            return jsonify(error="Bearer token is required"), 401, {"WWW-Authenticate": "Bearer"}

        try:
            payload = jwt.decode(
                authorization[1],
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
                options={"require": ["sub", "iat", "exp"]},
            )
            if payload["sub"] != current_app.config["IOT_USERNAME"]:
                raise jwt.InvalidTokenError("Invalid subject")
        except jwt.ExpiredSignatureError:
            return jsonify(error="Token has expired"), 401, {"WWW-Authenticate": "Bearer"}
        except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError):
            return jsonify(error="Invalid token"), 401, {"WWW-Authenticate": "Bearer"}

        return view(*args, **kwargs)

    return wrapped
