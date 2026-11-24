# System IoT

Projekt na Bezpieczeństwo systemów IoT, temat 25.
Flask przyjmuje pomiary temperatury i wilgotności z symulatora.
Logowanie zwraca token JWT ważny przez 15 minut.

## Uruchomienie

Python 3.10 lub nowszy. W PowerShell, w katalogu repozytorium:

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

## Symulator

Kilka czujników w jednym uruchomieniu:

```powershell
python sensor_simulator.py --device-id sensor-01 --device-id sensor-02 --count 5 --interval 1
```

- `--device-id` można powtarzać; bez tej opcji używany jest `sensor-01`. Identyfikatory muszą być poprawne i różne.
- `--count` to liczba rund (domyślnie 10). Każdy czujnik wysyła jeden pomiar w rundzie, więc przykład daje 10 pomiarów.
- `--interval` to przerwa między rundami w sekundach, od 0 do 86400 (domyślnie 1). Wysyłka jest kolejna, bez wątków; po ostatniej rundzie nie ma przerwy.
- `--url` zmienia adres API; domyślnie jest brany z `IOT_API_URL` lub wynosi `http://127.0.0.1:5000`.
- `--seed` pozwala powtórzyć wartości temperatury i wilgotności; znaczniki czasu nadal pochodzą z bieżącego zegara.

Wszystkie czujniki korzystają z jednej sesji i konta `IOT_USERNAME` / `IOT_PASSWORD`.
Symulator loguje do konsoli rundę, identyfikator czujnika, wynik wysyłki i ponowne logowanie po `401`.
Na końcu wypisuje liczbę potwierdzonych pomiarów i błędów łącznie oraz dla każdego czujnika.
Niepoprawne potwierdzenie `201` jest liczone jako błąd, bez ponawiania POST-a — pomiar mógł już zostać zapisany.
Kod zakończenia: `0` — wszystkie pomiary potwierdzone, `1` — błąd logowania lub pomiaru, `2` — błędne argumenty.

## API

- `GET /api/status` — stan serwera i liczba pomiarów.
- `POST /api/auth/login` — JSON z polami `username` i `password`; zwraca `access_token`.
- `POST /api/measurements` — JSON z `device_id` i `temperature`, opcjonalnie `humidity` i `timestamp` (ISO 8601).
- `GET /api/measurements` — lista zapisanych pomiarów w JSON, od najstarszego do najnowszego; gdy brak pomiarów, zwraca `[]`.
- `GET /api/measurements/stats` — liczba pomiarów (`count`) oraz `min`, `max`, `avg` temperatury i wilgotności.

Przykładowy pomiar: `{"device_id": "sensor-01", "temperature": 22.5, "humidity": 45}`.
Temperatura musi być w zakresie -50–100 °C, wilgotność 0–100%.
`device_id` ma od 1 do 64 znaków: litery ASCII, cyfry, `-` lub `_`, bez spacji i znaków nowej linii.

Statystyki obejmują pomiary aktualnie w pamięci. Średnie są zaokrąglane do dwóch miejsc,
a brakujące wartości wilgotności są pomijane. Bez pomiarów odpowiedź to
`{"count": 0, "temperature": null, "humidity": null}`; brak wilgotności oznacza `humidity: null`.

Wysyłanie i pobieranie pomiarów oraz statystyk wymaga nagłówka `Authorization: Bearer <access_token>`.
Token pobiera się przez logowanie. API sprawdza podpis HS256, czas ważności i pola
`sub`, `iat`, `exp`; brak tokenu, token błędny lub wygasły zwraca `401`.
Status serwera i logowanie są dostępne bez tokenu.

Symulator loguje się danymi z `IOT_USERNAME` (domyślnie `admin`) i `IOT_PASSWORD`,
a następnie wysyła pomiary z JWT. Po odpowiedzi `401` pobiera nowy token i ponawia pomiar raz.
Ostatnie 1000 pomiarów jest trzymane w pamięci i znika po wyłączeniu serwera.
Serwer służy do uruchamiania lokalnie, bez HTTPS.

## Błędy

Błędy API są zwracane jako JSON z polem `error`, np. `{"error": "Not Found"}`.

- `400` — błędne dane lub niepoprawny JSON.
- `401` — błędny login lub hasło, brak tokenu JWT albo token niepoprawny lub wygasły.
- `404` — nieistniejący endpoint (`Not Found`).
- `405` — niedozwolona metoda HTTP (`Method Not Allowed`); nagłówek `Allow` zawiera dozwolone metody.
- `413` — przekroczony limit treści żądania 16 KiB (`Request Entity Too Large`).
- `500` — nieoczekiwany błąd serwera (`Internal Server Error`), bez szczegółów wyjątku w odpowiedzi.

Niepoprawny Unicode w danych logowania i zbyt głęboko zagnieżdżony JSON zwracają `400`,
a zbyt głęboko zagnieżdżony JWT — `401`.

## Logi serwera

Logi trafiają do konsoli i pliku `logs/iot.log` w katalogu repozytorium (UTF-8).
Po osiągnięciu 1 MiB plik jest rotowany; zachowywane są trzy kopie: `.1`, `.2`, `.3`.
Każde żądanie ma wpis z metodą, ścieżką, kodem odpowiedzi, czasem obsługi i loginem
po poprawnym uwierzytelnieniu (`None` dla żądań nieuwierzytelnionych).
Poziomy: `INFO` dla poprawnych żądań i zdarzeń, `WARNING` dla błędów `4xx` i JWT,
`ERROR` dla błędów `5xx`. Nieoczekiwane wyjątki mają ślad stosu w logach, nie w odpowiedzi API.
Zapisywane są też logowania, odrzucone i przyjęte pomiary z identyfikatorem czujnika.
Treści żądań, hasła, tokeny i nagłówek `Authorization` nie są logowane.
Katalog `logs/` jest pomijany przez Git. Symulator loguje oddzielnie do konsoli, nie do pliku serwera.
