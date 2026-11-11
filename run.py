
import logging
import os

from iot_api import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("IOT_HOST", "127.0.0.1"),
        port=int(os.environ.get("IOT_PORT", "5000")),
    )
