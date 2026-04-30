# Project Structure

```
.
├── main.py                  # Entry point — wires login, data fetch, and simulation
├── login.py                 # Auth — returns a requests.Session with Brain API credentials
├── data_set.py              # Data fetching — paginated GET /data-fields, returns DataFrame
├── mock.py                  # Alpha generation & simulation — builds expressions, POSTs to /simulations
├── test.py                  # Tests
├── brain_credentials.txt    # Local credentials [username, password] — do not commit
└── file/
    └── fundamental6_data.csv  # Exported data field results
```

## Conventions

- Single responsibility per module: auth, data fetch, simulation, orchestration
- `main.py` wires modules together — no business logic there
- The `requests.Session` object (`sess`) is created once in `login.py` and passed through all functions
- Paginated responses use offset increments of 50; loop breaks when `len(results) < 50`
- Simulation polling uses the `Location` response header and respects `Retry-After` delays
- CSV exports go into the `file/` directory
- Comments and print statements are in Chinese — maintain this convention
- `brain_credentials.txt` must never be committed; use environment variables in CI/CD
