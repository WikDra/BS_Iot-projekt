import argparse
import datetime as dt
import logging
import math
import os
import random
import re
import sys
import time

import requests

DEFAULT_URL = os.environ.get("IOT_API_URL", "http://127.0.0.1:5000")
MAX_INTERVAL = 86400
logger = logging.getLogger("iot_simulator")


def generate_measurement(device_id, rng):
    return {
        "device_id": device_id,
        "temperature": round(rng.uniform(18.0, 28.0), 2),
        "humidity": round(rng.uniform(30.0, 70.0), 1),
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


def _positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("musi być >= 1")
    return number


def _interval(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= MAX_INTERVAL:
        raise argparse.ArgumentTypeError(f"musi być skończoną liczbą od 0 do {MAX_INTERVAL}")
    return number


def _device_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise argparse.ArgumentTypeError("wymagane 1-64 znaków: litery ASCII, cyfry, '-' lub '_'")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Symulator czujników IoT wysyłający pomiary do API")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"adres API (domyślnie {DEFAULT_URL})")
    parser.add_argument(
        "--device-id", dest="device_ids", action="append", type=_device_id,
        help="identyfikator czujnika; można podać kilka razy (domyślnie sensor-01)",
    )
    parser.add_argument("--count", type=_positive_int, default=10, help="liczba rund, czyli pomiarów każdego czujnika")
    parser.add_argument("--interval", type=_interval, default=1.0, help=f"przerwa między rundami [s], 0-{MAX_INTERVAL}")
    parser.add_argument("--seed", type=int, help="ziarno generatora (powtarzalne wartości pomiarów)")
    args = parser.parse_args(argv)
    args.device_ids = args.device_ids or ["sensor-01"]
    if len(set(args.device_ids)) != len(args.device_ids):
        parser.error("identyfikatory czujników nie mogą się powtarzać")
    return args


def login(session, base_url, username, password):
    try:
        response = session.post(
            base_url.rstrip("/") + "/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise ValueError(f"Nie udało się połączyć z API podczas logowania ({type(exc).__name__})") from None
    if response.status_code != 200:
        raise ValueError(f"Logowanie odrzucone: HTTP {response.status_code}")
    try:
        data = response.json()
    except (ValueError, RecursionError):
        raise ValueError("API zwróciło niepoprawny JSON podczas logowania") from None
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("access_token"), str)
        or not data["access_token"]
    ):
        raise ValueError("API nie zwróciło tokenu JWT")
    session.headers["Authorization"] = "Bearer " + data["access_token"]
    logger.info("Zalogowano do API")


def _valid_record(record):
    if not isinstance(record, dict):
        return False
    record_id = record.get("id")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id < 1:
        return False
    for field, low, high in (("temperature", -50, 100), ("humidity", 0, 100)):
        value = record.get(field)
        if field == "humidity" and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            return False
    return True


def send_measurement(session, base_url, measurement, username, password):
    url = base_url.rstrip("/") + "/api/measurements"
    try:
        response = session.post(url, json=measurement, timeout=5)
        if response.status_code == 401:
            logger.warning("device_id=%s otrzymano 401 — ponowne logowanie", measurement["device_id"])
            login(session, base_url, username, password)
            response = session.post(url, json=measurement, timeout=5)
    except requests.RequestException as exc:
        raise ValueError(
            f"Błąd wysyłania ({type(exc).__name__}); pomiar mógł zostać zapisany"
        ) from None
    if response.status_code != 201:
        raise ValueError(f"API odrzuciło pomiar: HTTP {response.status_code}")
    try:
        record = response.json()
        if not _valid_record(record):
            raise ValueError
    except (ValueError, RecursionError):
        raise ValueError(
            "Niepoprawne potwierdzenie HTTP 201; pomiar mógł zostać zapisany, nie ponawiam wysyłki"
        ) from None
    return record


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.setLevel(logging.INFO)
    username = os.environ.get("IOT_USERNAME", "admin")
    password = os.environ.get("IOT_PASSWORD")
    if not password:
        logger.error("Ustaw zmienną środowiskową IOT_PASSWORD (hasło użytkownika API)")
        return 1

    rng = random.Random(args.seed)
    counts = {device_id: {"sent": 0, "failed": 0} for device_id in args.device_ids}
    with requests.Session() as session:
        try:
            login(session, args.url, username, password)
        except ValueError as exc:
            logger.error("%s", exc)
            return 1

        for round_number in range(1, args.count + 1):
            for device_id in args.device_ids:
                measurement = generate_measurement(device_id, rng)
                try:
                    record = send_measurement(session, args.url, measurement, username, password)
                except ValueError as exc:
                    counts[device_id]["failed"] += 1
                    logger.error(
                        "runda=%d/%d device_id=%s %s", round_number, args.count, device_id, exc
                    )
                else:
                    counts[device_id]["sent"] += 1
                    humidity = record.get("humidity")
                    humidity_text = "brak" if humidity is None else f"{humidity:.1f} %"
                    logger.info(
                        "runda=%d/%d device_id=%s zapisano pomiar id=%d: %.2f °C, wilgotność=%s",
                        round_number, args.count, device_id, record["id"],
                        record["temperature"], humidity_text,
                    )
            if round_number < args.count:
                time.sleep(args.interval)

    sent = sum(count["sent"] for count in counts.values())
    failed = sum(count["failed"] for count in counts.values())
    logger.info("Podsumowanie: potwierdzone=%d błędy=%d", sent, failed)
    for device_id, count in counts.items():
        logger.info(
            "device_id=%s potwierdzone=%d błędy=%d", device_id, count["sent"], count["failed"]
        )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
