# Frame Background Removal API

Standalone Python API for removing image backgrounds (PNG output with transparency).

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

export BG_API_TOKEN="change-me"
export BG_MAX_UPLOAD_BYTES=10485760

.venv/bin/uvicorn bg_remove_api:app --host 0.0.0.0 --port 8080
```

## Endpoints

- `GET /health`
- `POST /remove-background` (multipart field: `file`)

## Authentication

Send one of:

- `Authorization: Bearer <token>`
- `X-API-Token: <token>`

## Example request

```bash
curl -X POST "http://localhost:8080/remove-background" \
  -H "Authorization: Bearer change-me" \
  -F "file=@person.jpg" \
  --output person-cutout.png
```

## DigitalOcean Functions (doctl serverless)

A ready-to-deploy DO Functions project is included under `functions/`.

### Structure

- `functions/project.yml`
- `functions/packages/default/removebg/__main__.py`

### Deploy steps

```bash
# one-time
#doctl auth init
#doctl serverless install
#doctl serverless connect

cd functions
export BG_API_TOKEN="your-internal-token"
export REMOVE_BG_API_KEY="your-removebg-key"
doctl serverless deploy .
```

### Invoke example

After deploy, get URL:

```bash
doctl serverless functions get default/removebg --url
```

Call it with base64 payload:

```bash
curl -X POST "<FUNCTION_URL>" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BG_API_TOKEN" \
  -d '{"image_base64":"<BASE64_IMAGE>"}'
```
