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

W drugim terminalu (z aktywnym środowiskiem) ustaw to samo hasło:

```powershell
$env:IOT_PASSWORD = "wlasne-haslo"
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

Wysyłanie i pobieranie pomiarów wymaga nagłówka `Authorization: Bearer <access_token>`.
Token pobiera się przez logowanie. API sprawdza podpis HS256, czas ważności i pola
`sub`, `iat`, `exp`; brak tokenu, token błędny lub wygasły zwraca `401`.
Status serwera i logowanie są dostępne bez tokenu.

Symulator loguje się danymi z `IOT_USERNAME` (domyślnie `admin`) i `IOT_PASSWORD`,
a następnie wysyła pomiary z JWT. Po odpowiedzi `401` pobiera nowy token i ponawia pomiar raz.
Ostatnie 1000 pomiarów jest trzymane w pamięci i znika po wyłączeniu serwera.
Serwer służy do uruchamiania lokalnie, bez HTTPS.