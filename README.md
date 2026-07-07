# Cloud Sync Service

Ein kleiner Python-Service, der JSON-Daten aus einer Cloud-API lädt, normalisiert,
per Upsert in SQLite speichert und über eine REST-API bereitstellt.

## Starten

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Danach ist die interaktive API-Dokumentation unter
<http://127.0.0.1:8000/docs> erreichbar.

## Endpunkte

- `POST /sync` – Daten aus der Cloud abrufen und speichern
- `GET /items` – gespeicherte Daten lesen (`limit` und `offset` möglich)
- `GET /items/{id}` – einzelnen Datensatz lesen
- `GET /health` – Status prüfen

Beispiel:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/sync
Invoke-RestMethod http://127.0.0.1:8000/items?limit=5
```

## Konfiguration

Die Einstellungen werden aus Umgebungsvariablen oder einer lokalen `.env`-Datei
gelesen. Dazu kann `.env.example` nach `.env` kopiert werden. Für APIs mit Schlüssel wird automatisch der Header
`Authorization: Bearer <CLOUD_API_KEY>` gesendet. Die Antwort darf entweder eine
JSON-Liste sein oder ein Objekt mit einem Feld `items` beziehungsweise `data`.
