# 🇱🇻 Latvian Language Agent

A personal AI-powered system for learning Latvian.

The project combines a Telegram bot, an AI lesson generator, a vocabulary database, and a browser bookmarklet for collecting Latvian words from Yandex Translate.

## Features

* 🇱🇻 Generate Latvian language lessons with Russian translations
* 🤖 Telegram bot interface
* 📚 Persistent vocabulary collection
* 🔤 Latvian words stored together with Russian translations
* 📐 Grammar information for each word
* 📝 Full and short lesson formats
* 🌐 Import vocabulary from a Yandex Translate collection
* 🔖 Browser bookmarklet for vocabulary synchronization
* 🔄 FastAPI synchronization server
* 🐳 Docker-based deployment

## Architecture

```text
                    ┌─────────────────────┐
                    │   Yandex Translate  │
                    │      Collection     │
                    └──────────┬──────────┘
                               │
                         Bookmarklet
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Browser        │
                    └──────────┬──────────┘
                               │
                            Sync API
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│                     VPS / Docker                        │
│                                                         │
│  ┌─────────────────┐       ┌──────────────────────┐     │
│  │  Telegram Bot   │       │  vocabulary-sync     │     │
│  │    bot.py       │       │  FastAPI             │     │
│  └────────┬────────┘       └────────────┬─────────┘     │
│           │                             │               │
│           ▼                             ▼               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Vocabulary / Lesson data            │   │
│  │                                                  │   │
│  │  vocabulary.json       lesson_cache.json         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```text
latvian-agent/
│
├── bot.py
├── sync_server.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
├── .gitignore
│
├── vocabulary.json        # local runtime data
├── lesson_cache.json      # local runtime data
│
└── README.md
```

Runtime data and secrets are intentionally excluded from Git.

## Telegram Bot

`bot.py` implements the Telegram interface.

The bot can:

* generate Latvian lessons;
* provide Russian translations;
* explain Latvian grammar;
* work with vocabulary collected by the user;
* provide both detailed and short versions of vocabulary explanations.

### Full lesson format

The full format contains:

```text
Lemma
Part of speech
Form
Grammar
Latvian example
Russian translation
Explanation
```

Example:

```text
šķēršļiem — препятствия

Lemma: šķērslis
Part of speech: lietvārds
Form: šķēršļiem
Grammar: Dative plural

Par spīti šķēršļiem mēs turpinājām ceļu.

Несмотря на препятствия, мы продолжили путь.
```

### Short format

The short format is intentionally compact:

```text
šķēršļiem — препятствия

(Dative plural)
```

The short format is designed for quick vocabulary review.

## Vocabulary Synchronization

The synchronization server is implemented in `sync_server.py`.

It exposes:

```text
POST /sync
```

The request body is a JSON array:

```json
[
  {
    "lv": "šķēršļiem",
    "ru": "препятствия",
    "score": 0,
    "id": "example-id"
  }
]
```

The server validates the synchronization token and writes the resulting vocabulary to:

```text
/app/vocabulary.json
```

A successful response looks like:

```json
{
  "status": "ok",
  "count": 1
}
```

## API

### POST `/sync`

Headers:

```text
Content-Type: application/json
X-Sync-Token: <SYNC_TOKEN>
```

Body:

```json
[
  {
    "lv": "atbilstoši",
    "ru": "согласно",
    "score": 0
  }
]
```

Example using `curl`:

```bash
curl -X POST https://webscraping.pro/latvian-sync \
  -H "Content-Type: application/json" \
  -H "X-Sync-Token: YOUR_TOKEN" \
  -d '[{"lv":"atbilstoši","ru":"согласно","score":0}]'
```

Expected response:

```json
{
  "status": "ok",
  "count": 1
}
```

## Browser Bookmarklet

The project uses a browser bookmarklet to collect Latvian vocabulary from a Yandex Translate collection.

The bookmarklet is saved as a normal browser bookmark, but its URL starts with:

```text
javascript:
```

The code:

```text
javascript:(async()=>{try{const id='6a926bb9d12c1b66457218ee';const r=await fetch('/props/api/collections/'+id+'?srv=tr-text&uid=207946218');if(!r.ok)throw new Error('Yandex API HTTP '+r.status);const d=await r.json();const words=(d.collection?.records||[]).map(x=>({lv:x.text,ru:x.translation,score:x.score||0,id:x.id}));if(!words.length)throw new Error('No words found');const f=document.createElement('form');f.method='POST';f.action='https://webscraping.pro/latvian-sync';f.target='_blank';const w=document.createElement('input');w.type='hidden';w.name='words';w.value=JSON.stringify(words);const t=document.createElement('input');t.type='hidden';t.name='token';t.value='YOUR-SECRET_TOKEN';f.append(w,t);document.body.appendChild(f);f.submit();f.remove()}catch(e){console.error(e);alert('❌ Sync failed\n\n'+e.message)}})()
```
Replace in the above bookmarklet `YOUR-SECRET_TOKEN` with actual secret code from `.env`

### Installation

1. Open Chrome.
2. Create a new bookmark.
3. Give it a name such as:

```text
🇱🇻 Sync Latvian Vocabulary
```

4. Paste the bookmarklet JavaScript into the bookmark URL.
5. Open the Yandex Translate collection.
6. Run the bookmarklet.

### Security

The synchronization endpoint is protected by `SYNC_TOKEN`.

The token is stored in `.env`:

```text
SYNC_TOKEN=your-secret-token
```

`.env` is excluded from Git through `.gitignore`.

**Never commit `.env` to GitHub.**

## Docker

The project can be run with Docker Compose.

Build and start:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

## Environment Variables

Create `.env` locally:

```text
SYNC_TOKEN=your-secret-token
```

Additional variables used by the Telegram bot should also be stored in `.env`.

Do not commit `.env`.

## Nginx

The synchronization API is exposed through the main web server:

```text
https://webscraping.pro/latvian-sync
```

Nginx proxies the request to the internal FastAPI service:

```text
 webscraping.pro
       │
       ▼
     Nginx
       │
       ▼
127.0.0.1:8081
       │
       ▼
 FastAPI /sync
```

The FastAPI service itself does not need to be publicly exposed.

## Development

Clone the repository:

```bash
git clone git@github.com:igorsavinkin/latvian-language-agent.git
cd latvian-language-agent
```

Create the environment file:

```bash
cp .env.example .env
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the bot:

```bash
python bot.py
```

Run the synchronization server:

```bash
uvicorn sync_server:app --host 0.0.0.0 --port 8081
```

## Git Security

The following files are intentionally ignored:

```text
.env
.env.*
vocabulary.json
lesson_cache.json
*.save
bot_old.py
```

This keeps:

* API tokens
* Telegram credentials
* vocabulary runtime data
* lesson cache
* backups

out of the public repository.

## Roadmap

Possible future improvements:

* [ ] PostgreSQL instead of JSON storage
* [ ] Vocabulary import/export
* [ ] Spaced repetition
* [ ] Word difficulty scoring
* [ ] Automatic review scheduling
* [ ] User statistics
* [ ] Telegram inline vocabulary review
* [ ] Audio pronunciation
* [ ] Latvian speech recognition
* [ ] Better grammar analysis
* [ ] Automated tests
* [ ] CI/CD
* [ ] Web interface for vocabulary management

## Goal

The goal of the project is to build a practical personal Latvian-learning system where vocabulary collected during everyday language study can automatically become part of an AI-assisted learning workflow.
