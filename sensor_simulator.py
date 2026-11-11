
import argparse
import datetime as dt
import os
import random
import sys
import time

import requests

DEFAULT_URL = os.environ.get("IOT_API_URL", "http://127.0.0.1:5000")


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


def _non_negative_float(value):
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("musi być >= 0")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Symulator czujnika IoT wysyłający pomiary do API")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"adres API (domyślnie {DEFAULT_URL})")
    parser.add_argument("--device-id", default="sensor-01", help="identyfikator czujnika")
    parser.add_argument("--count", type=_positive_int, default=10, help="liczba pomiarów do wysłania")
    parser.add_argument("--interval", type=_non_negative_float, default=1.0, help="odstęp między pomiarami [s]")
    parser.add_argument("--seed", type=int, help="ziarno generatora (powtarzalne dane)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rng = random.Random(args.seed)
    sent = 0
    failed = 0
    url = args.url.rstrip("/") + "/api/measurements"

    with requests.Session() as session:
        for i in range(1, args.count + 1):
            measurement = generate_measurement(args.device_id, rng)
            prefix = f"[{i}/{args.count}]"
            try:
                response = session.post(url, json=measurement, timeout=5)
            except requests.RequestException as exc:
                failed += 1
                print(f"{prefix} błąd połączenia: {exc}", file=sys.stderr)
            else:
                if response.status_code == 201:
                    sent += 1
                    record = response.json()
                    print(
                        f"{prefix} wysłano #{record['id']}: {record['temperature']:.2f} °C, "
                        f"{record['humidity']:.1f} %"
                    )
                else:
                    failed += 1
                    print(
                        f"{prefix} API odrzuciło pomiar: HTTP {response.status_code} "
                        f"{response.text.strip()}",
                        file=sys.stderr,
                    )

            if i < args.count:
                time.sleep(args.interval)

    print(f"Wysłano: {sent}, błędy: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
