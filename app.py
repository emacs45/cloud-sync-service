import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv


load_dotenv()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/service.db"))
CLOUD_API_URL = os.getenv(
    "CLOUD_API_URL", "https://jsonplaceholder.typicode.com/posts"
)
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY")


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                payload TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )


def fetch_cloud_data() -> list[dict[str, Any]]:
    headers = {"Accept": "application/json", "User-Agent": "cloud-sync-service/1.0"}
    if CLOUD_API_KEY:
        headers["Authorization"] = f"Bearer {CLOUD_API_KEY}"

    request = Request(CLOUD_API_URL, headers=headers)
    with urlopen(request, timeout=20) as response:  # noqa: S310
        data = json.load(response)

    if isinstance(data, dict):
        data = data.get("items", data.get("data", [data]))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("Die Cloud-API muss eine JSON-Liste mit Objekten liefern.")
    return data


def process_item(item: dict[str, Any], position: int) -> dict[str, str]:
    external_id = str(item.get("id", item.get("uuid", position)))
    raw_title = item.get("title", item.get("name", f"Eintrag {external_id}"))
    title = " ".join(str(raw_title).strip().split())
    return {
        "external_id": external_id,
        "title": title[:500],
        "payload": json.dumps(item, ensure_ascii=False, separators=(",", ":")),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def save_items(items: list[dict[str, Any]]) -> int:
    processed = [process_item(item, index) for index, item in enumerate(items, start=1)]
    with connect() as db:
        db.executemany(
            """
            INSERT INTO items (external_id, title, payload, fetched_at)
            VALUES (:external_id, :title, :payload, :fetched_at)
            ON CONFLICT(external_id) DO UPDATE SET
                title = excluded.title,
                payload = excluded.payload,
                fetched_at = excluded.fetched_at
            """,
            processed,
        )
    return len(processed)


def serialize(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    return result


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Cloud Sync Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sync")
def sync() -> dict[str, Any]:
    try:
        count = save_items(fetch_cloud_data())
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Cloud-Abruf fehlgeschlagen: {error}") from error
    return {"status": "ok", "processed": count}


@app.get("/items")
def list_items(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM items ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [serialize(row) for row in rows]


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    return serialize(row)
