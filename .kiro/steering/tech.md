# Tech Stack

## Language
- Python 3

## Libraries
- `requests` — HTTP client for Brain API calls
- `pandas` — DataFrame handling for data fields
- `curlify` — Debug utility to convert requests to curl commands
- `time` — Polling/retry delays

## Authentication
- HTTP Basic Auth via `requests.auth.HTTPBasicAuth`
- Credentials loaded from `brain_credentials.txt` (JSON array `[username, password]`)
- Falls back to environment variables `BRAIN_USERNAME` / `BRAIN_PASSWORD`

## API
- Base URL: `https://api.worldquantbrain.com`
- Key endpoints:
  - `POST /authentication` — establish session
  - `GET /data-fields` — paginated field fetch (limit 50, offset-based)
  - `POST /simulations` — submit alpha simulation
  - `GET {Location}` — poll simulation progress via `Retry-After` header

## Common Commands
```bash
# Run the main pipeline
python main.py

# Run tests
python test.py
```
