from datetime import datetime, timedelta, timezone

import jwt


def create_access_token(username, secret, expires_in=900):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
