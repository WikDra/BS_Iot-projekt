# System IoT

Projekt na Bezpieczeństwo systemów IoT, temat 25.
Flask przyjmuje pomiary temperatury i wilgotności z symulatora.
Logowanie zwraca token JWT ważny przez 15 minut.

## Uruchomienie

Python 3.10 lub nowszy. W PowerShell, w katalogu `iot_system`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:IOT_PASSWORD = "wlasne-haslo"
python run.py
```

W drugim terminalu (z aktywnym środowiskiem):

```powershell
python sensor_simulator.py --count 5 --interval 1
```

API działa pod `http://127.0.0.1:5000`. Login to `admin` (można zmienić przez
`IOT_USERNAME`), hasło jest brane z `IOT_PASSWORD`. Klucz JWT jest losowany przy
starcie; własny, co najmniej 32-znakowy, można ustawić przez `IOT_JWT_SECRET`.

## API

- `GET /api/status` — stan serwera i liczba pomiarów.
- `POST /api/auth/login` — JSON z polami `username` i `password`; zwraca `access_token`.
- `POST /api/measurements` — JSON z `device_id` i `temperature`, opcjonalnie `humidity` i `timestamp` (ISO 8601).
- `GET /api/measurements` — lista zapisanych pomiarów w JSON, od najstarszego do najnowszego; gdy brak pomiarów, zwraca `[]`.

Przykładowy pomiar: `{"device_id": "sensor-01", "temperature": 22.5, "humidity": 45}`.
Temperatura musi być w zakresie -50–100 °C, wilgotność 0–100%.

Na tym etapie wysyłanie i pobieranie pomiarów nie wymaga tokenu. Ostatnie 1000 pomiarów jest trzymane w pamięci
i znika po wyłączeniu serwera. Serwer służy do uruchamiania lokalnie, bez HTTPS.