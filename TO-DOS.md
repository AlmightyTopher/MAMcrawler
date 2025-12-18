## Security & Refactor Roadmap - 2025-12-16 16:35

- [x] **Lock Down** API Control Plane - Secure the FastAPI interface.
  - **Problem:** `api_server.py` binds to `0.0.0.0:8081` by default with `app = FastAPI()`, no authentication middleware, and no CSRF protection. Any LAN user can POST to `/api/control/top-search`.
  - **Files:** `api_server.py`, `config.py`
  - **Solution:**
    1. [x] Bind to `127.0.0.1` by default in `api_server.py`.
    2. [x] Implement `API Key` or `Session` authentication middleware.
    3. [x] Define Viewer/Operator/Admin roles. (Implemented Admin role)
    4. [x] Add CSRF protection and Rate limiting.

- [x] **Secure** Secrets & Logs - Prevent credential leakage.
  - **Problem:** `mam_selenium_crawler.py` saves session cookies to `mam_cookies.json` in plaintext. `master_audiobook_manager.py` redirects raw `sys.stdout/stderr` to log files, capturing any debug prints of secrets.
  - **Files:** `mam_selenium_crawler.py`, `master_audiobook_manager.py`, `logging_system.py`
  - **Solution:**
    1. [x] Encrypt `mam_cookies.json` using a local key (Keychain/KMS).
    2. [x] configure a proper logging handler that sanitizes sensitive patterns (API keys, passwords) before writing to disk.
    3. [x] Use structured monitoring (Sentry/OpenTelemetry) instead of file redirection.

- [x] **Refactor** Job System - Replace subprocesses with reliable queue.
  - **Problem:** `api_server.py` uses a global `current_process` variable to track jobs. Server restarts leave orphaned `subprocess.Popen` tasks running with no UI visibility or history.
  - **Files:** `api_server.py`, `master_audiobook_manager.py`
  - **Solution:**
    1. [x] Move task logic In-process (async) or use a robust worker.
    2. [x] Implement durable queue (Redis/SQLite-backed) to persist job state across restarts. (Used APScheduler + PostgreSQL)
    3. [x] Create a Job table (status, history, logs).
    4. [x] Enforce currency control (singleton Selenium session).

- [x] **Harden** Selenium - Make automation survivable.
  - **Problem:** `selenium_integration.py` clicks Prowlarr UI elements by CSS class/ID, which is brittle. `mam_selenium_crawler.py` has no recovery if Chrome crashes.
  - **Files:** `selenium_integration.py`, `mam_selenium_crawler.py`
  - **Solution:**
    1. [x] Switch Prowlarr integration to use the Prowlarr API completely.
    2. [x] Implement a Browser watchdog/restart mechanism.
    3. [x] Use deterministic waits (WebDriverWait) instead of `time.sleep()`.
    4. [x] Handle 2FA/Captcha logic gracefully (pause execution/notify user).

- **Unify** Configuration - Single source of truth.
  - **Problem:** Hardcoded URLs (e.g., Prowlarr in `selenium_integration.py`) exist despite `config_system.py`. `config.py` is a shim.
  - **Files:** `config.py`, `selenium_integration.py`, `config_system.py`
  - **Solution:**
    1. Enforce usage of `ConfigSystem` in all modules.
    2. Remove all hardcoded fallbacks and strictly validate via Pydantic.
    3. Add a "Config doctor" CLI command to validate environment.

- [x] **Consolidate** Data - Postgres as truth.
  - **Problem:** State is split between `metadata.sqlite`, `mam_stats.json`, `active_status.json`, and PostgreSQL.
  - **Files:** `database/`, `unified_metadata_aggregator.py`
  - **Solution:**
    1. [x] Migrate all state (items, history, cache, stats) to PostgreSQL. (StatusReporter now uses DB)
    2. Use Alembic for schema migrations.
    3. Implement Idempotency constraints on download queuing.

- **Prepare** Production Deployment - Service user, TLS, Monitoring.
  - **Problem:** Application runs as the current user, exposing user files. No TLS for the web dashboard.
  - **Files:** `deployment/`
  - **Solution:**
    1. Run as a dedicated service user.
    2. Use Gunicorn/Systemd for process management.
    3. proper Reverse Proxy (Nginx/Caddy) with TLS.
    4. Health checks & Prometheus metrics endpoint.

- **Verify** Quality - Automated tests.
  - **Problem:** Lack of security/integration tests.
  - **Files:** `tests/`
  - **Solution:**
    1. Add Unit tests for config validation and log redaction.
    2. Add Integration tests for Auth and Job queuing.
    3. Add SAST/Dependency scanning to CI.
    4. Ensure reproducible builds (Docker).

- **Validate** Claims - Ensure "Production Ready" is true.
  - **Solution:**
    - Config: No hardcoded ports/URLs.
    - Prod: Auth everywhere, encrypted secrets.
    - DB: Single authoritative source.

- **Execute** Order of Operations - Strict sequence.
  1. Bind localhost + Auth.
  2. Sanitize logs.
  3. Encrypt secrets.
  4. Job queue.
  5. Remove brittle UI clicking.
  6. Unify config.
  7. Postgres consolidation.
  8. Health checks/metrics.
  9. CI/Tests.
  10. Deploy.
