# FirstTry Licensing (FastAPI)

Endpoints:
- `GET /health` → `{"ok": true}`
- `POST /v1/license/verify` → `{ valid, reason, features }`
- `POST /v1/webhook/stripe` (stub)
- `POST /v1/webhook/lemonsqueezy` (stub)

## Config
- `FIRSTTRY_KEYS` — comma-separated keys, with optional features:
  - `ABC123` (no features)
  - `PRO456:featA|featB`

## Run locally
```bash
export FIRSTTRY_KEYS="ABC123:featX|featY"
export PYTHONPATH=licensing
uvicorn app.main:app --host 127.0.0.1 --port 8081 --reload
```

Verify:

```bash
curl -s http://127.0.0.1:8081/health
curl -s -X POST http://127.0.0.1:8081/v1/license/verify \
  -H 'content-type: application/json' \
  -d '{"product":"firsttry","key":"ABC123"}'
```

---

## Optional (nice-to-have) quick sanity run, then push

```bash
# python side
. .venv/bin/activate || python -m venv .venv && . .venv/bin/activate
pip install -e tools/firsttry fastapi uvicorn pydantic
make licensing-test
make py-validate
```
