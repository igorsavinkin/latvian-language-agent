import json
import os

from fastapi import FastAPI, Header, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


VOCABULARY_FILE = "/app/vocabulary.json"

SYNC_TOKEN = os.environ["SYNC_TOKEN"]


app = FastAPI(title="Latvian Vocabulary Sync")


# Keep CORS for the existing JSON /sync endpoint.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class Word(BaseModel):
    lv: str
    ru: str
    score: int = 0
    id: str | None = None


def save_words(data: list[dict]):
    with open(VOCABULARY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# Existing JSON endpoint.
# Do NOT remove this — it already works.
@app.post("/sync")
async def sync_words(
    words: list[Word],
    x_sync_token: str | None = Header(default=None),
):
    if x_sync_token != SYNC_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid sync token",
        )

    data = [word.model_dump() for word in words]

    save_words(data)

    return {
        "status": "ok",
        "count": len(data),
    }


# New endpoint for the Yandex bookmarklet.
#
# This endpoint receives a normal HTML form POST,
# so the browser does NOT need fetch() to webscraping.pro.
@app.post("/sync-form")
async def sync_form(
    words: str = Form(...),
    token: str = Form(...),
):
    if token != SYNC_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid sync token",
        )

    try:
        raw_words = json.loads(words)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in words field",
        )

    if not isinstance(raw_words, list):
        raise HTTPException(
            status_code=400,
            detail="Words must be a JSON array",
        )

    data = []

    for item in raw_words:
        if not isinstance(item, dict):
            continue

        if "lv" not in item or "ru" not in item:
            continue

        data.append(
            {
                "lv": str(item["lv"]),
                "ru": str(item["ru"]),
                "score": int(item.get("score", 0)),
                "id": item.get("id"),
            }
        )

    save_words(data)

    # Return a simple HTML result page.
    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Latvian Sync</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 80px auto;
                    text-align: center;
                    line-height: 1.6;
                }}
                .ok {{
                    font-size: 48px;
                }}
            </style>
        </head>
        <body>
            <div class="ok">🇱🇻</div>
            <h1>Sync successful</h1>
            <p>✅ {len(data)} Latvian words synchronized.</p>
            <p>You can close this tab.</p>
        </body>
        </html>
        """,
        status_code=200,
    )

