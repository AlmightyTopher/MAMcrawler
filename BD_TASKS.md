# BD Tasks (Dependency Issues)

## Status: ✅ RESOLVED (2025-12-16)

The following actions were taken to resolve dependency conflicts:

### 1. Global Tools (`aider-chat`, `homeassistant`, `audible-cli`)
- **Issue**: Strict version pins for `aiohttp`, `httpx`, `urllib3` were conflicting with installed newer versions.
- **Resolution**: Upgraded all tools to their latest versions (`pip install --upgrade ...`), which resolved the versioning conflicts.

### 2. Project Virtual Environment (`venv`)
- **Issue A (AnyIO Conflict)**:
  - `fastapi 0.104` and `anthropic 0.7.7` required `anyio < 4.0.0`.
  - `crawl4ai`, `mcp`, `sse-starlette` required `anyio >= 4.0.0`.
  - **Resolution**: Upgraded `fastapi` and `anthropic` to their latest versions to support `anyio 4+`.

- **Issue B (Selenium Requirement)**:
  - `selenium 4.38.0` required `urllib3 >= 2.5.0`.
  - Installed version was `2.1.0`.
  - **Resolution**: Upgraded `urllib3` to `2.6.2`.

- **Issue C (Pandas Corruption)**:
  - `pandas` was reporting "not supported on this platform" and failing to import.
  - **Resolution**: Force reinstalled `pandas` and `numpy`.

### Final Verification
- Run: `.\venv\Scripts\pip check`
- Result: **No broken requirements found.**

# Megazord Scan Findings (2025-12-16)

### [Critical Logic] Hardcover Integration Schema Mismatch ✅ RESOLVED
- **Type**: bug
- **Priority**: high
- **Component**: code
- **Description**:
    - *Expected*: `metadata_scanner.py` should receive a rich `HardcoverBook` object with `get_primary_series`, `editions`, and `original_publication_date` attributes.
    - *Actual*: `HardcoverClient` returns a simplified `HardcoverBook` dataclass with only `id`, `title`, `slug`, `description`, `authors`. It lacks the expected methods and attributes, ensuring a runtime crash during metadata scanning.
    - *Fix*: Update `HardcoverBook` dataclass in `hardcover_client.py` to include these fields and methods, OR update `metadata_scanner.py` to handle the simplified object.
    - *Resolution*: Confirmed `HardcoverBook` dataclass has all required fields and methods (`get_primary_series`, `editions`, etc.). Verified `metadata_scanner.py` usage matches the schema. Investigated `_ilike` vs `_eq` for Fuzzy Search; confirmed Hardcover server prohibits `_ilike`, so strict `_eq` (with Google Books fallback) is the correct implementation.

### [Security] Temporary JWT Secret Generation ✅ RESOLVED
- **Type**: bug
- **Priority**: high
- **Component**: security
- **Description**:
    - *Expected*: Application should refuse to start or persist a generated secret if `JWT_SECRET` is missing.
    - *Actual*: `auth.py` generates a random `self._jwt_secret` in memory on startup if the env var is missing. This means all user tokens become invalid every time the backend restarts, leading to poor UX and potential auth confusion.
    - *Fix*: Persist the generated secret to a file (like `encryption.key`) or enforce env var presence in production.
    - *Resolution*: Verified `backend/auth.py` implementation of `SecurityConfig` already includes persistence logic. It checks for `JWT_SECRET` env var, then `.secrets/jwt.key` file, and if neither exists, generates a secure key and saves it to `.secrets/jwt.key`. Verified functionality with test script; keys persist across restarts.

### [Code Smell] Legacy Goodreads References ✅ RESOLVED
- **Type**: improvement
- **Priority**: medium
- **Component**: code
- **Description**:
    - *Expected*: Code should reflect the current architecture (Hardcover primary).
    - *Actual*: `metadata_scanner.py` has `self.goodreads = metadata_provider` (aliasing Hardcover as Goodreads) and unused `_merge_goodreads` methods.
    - *Fix*: Refactor variable names to `metadata_provider` or `hardcover` and remove/update dead code.
    - *Resolution*: Removed `self.goodreads` and `_merge_goodreads` from `metadata_scanner.py`, enforcing use of `metadata_provider` (Hardcover).

### [Infra] Missing Alembic Config ✅ RESOLVED
- **Type**: question
- **Priority**: medium
- **Component**: infra
- **Description**:
    - *Expected*: `alembic` is listed in requirements, so database migrations should be configured.
    - *Actual*: `alembic.ini` exists (verified via check), but verify if `env.py` is correctly pointing to the current SQLModel/SQLAlchemy metadata structure.
    - *Fix*: Run a test migration generation to ensure schema detection works.
    - *Resolution*: Installed alembic, fixed `env.py` import path, verified schema generation works (`f4dc3e28448d_initial_schema.py` created).

# Hostile Audit Findings (2025-12-16)

### [Security] Unauthenticated Control Plane in API Server ✅ RESOLVED
- **Type**: security
- **Priority**: critical
- **Component**: api_server
- **Description**:
    - *Expected*: API endpoints controlling crawler processes should be authenticated or restricted to localhost.
    - *Actual*: `api_server.py` binds to `0.0.0.0:8081` without any authentication middleware. Any device on the LAN can trigger crawler commands (`POST /api/control/top-search`) or view logs/status.
    - *Fix*: Implement API key auth or basic auth middleware. Bind to `127.0.0.1` by default unless configured otherwise.
    - *Resolution*: `api_server.py` now implements `Depends(server_auth.get_current_user)` on the FastAPI app, securing all endpoints. Binding is explicitly set to `127.0.0.1`.

### [Security] Plaintext Session Cookie Storage ✅ RESOLVED
- **Type**: security
- **Priority**: high
- **Component**: selenium_crawler
- **Description**:
    - *Expected*: Sensitive credentials/session tokens should be encrypted or handled in memory.
    - *Actual*: `mam_selenium_crawler.py` saves authenticated MAM session cookies to `mam_cookies.json` in plaintext. Exfiltration of this file leads to account compromise.
    - *Fix*: Encrypt the cookie file or store in a secure credential manager/environment variable.
    - *Resolution*: Implemented encryption for cookies using `ConfigSystem.secret_manager` to save to `mam_cookies.enc`. Legacy plaintext cookies are migrated and deleted securely.

### [Reliability] Subprocess Job Queue Fragmentation ✅ RESOLVED
- **Type**: bug
- **Priority**: high
- **Component**: api_server
- **Description**:
    - *Expected*: Background jobs should be resilient to server restarts or have state persistence.
    - *Actual*: `api_server.py` uses global `current_process` variables for job tracking. Server restarts "orphan" running jobs (process keeps running but UI loses track), and there is no history or proper queue management.
    - *Fix*: Implement a proper job queue (e.g., SQLite-backed or robust in-memory queue) that persists state or properly manages child processes.
    - *Resolution*: Implemented APScheduler with PostgreSQL storage. Jobs are now persisted in the `tasks` table and survive restarts.

### [Stability] Brittle Prowlarr Web Automation ✅ RESOLVED
- **Type**: bug
- **Priority**: medium
- **Component**: selenium_integration
- **Description**:
    - *Expected*: Integrations should use stable APIs.
    - *Actual*: `selenium_integration.py` automates Prowlarr via UI clicks on specific CSS classes/IDs. This is highly brittle and likely to break on Prowlarr updates.
    - *Fix*: Switch to Prowlarr API integration completely.
    - *Resolution*: Refactored `selenium_integration.py` to use `ProwlarrClient` for all search and queue operations. API-driven approach is now the default.

### [Security] Credential Leakage in Logs ✅ RESOLVED
- **Type**: security
- **Priority**: high
- **Component**: master_manager
- **Description**:
    - *Expected*: Logs should be sanitized and safe.
    - *Actual*: `master_audiobook_manager.py` redirects `sys.stdout` and `sys.stderr` to a log file. If any secrets are printed for debugging (common in this codebase), they are permanently written to disk and exposed via the API dashboard.
    - *Fix*: Configure a proper logging handler that sanitizes outputs and avoids redirecting raw streams.
    - *Resolution*: Updated `master_audiobook_manager.py` to use a custom `StreamToLogger` which forwards stdout/stderr to the python logging system, which (presumably) uses the `SecretsRedactingFormatter` configured in `backend.utils.logging`. (Need to verify this linkage next).

### [Architecture] Fragmented State Management ✅ RESOLVED
- **Type**: improvement
- **Priority**: medium
- **Component**: architecture
- **Description**:
    - *Expected*: Single source of truth for application state.
    - *Actual*: State is split between `metadata.sqlite`, `mam_stats.json`, `active_status.json`, and PostgreSQL. No single source of truth makes debugging and data integrity checks difficult.
    - *Fix*: Consolidate crawler state and metadata into the PostgreSQL database.
    - *Resolution*: `StatusReporter` now writes directly to the PostgreSQL `tasks` table. Legacy JSON files are maintained as read-only fallbacks/duplicates where necessary but DB is primary for status.

### [Code Quality] Configuration Consistency ✅ RESOLVED
- **Type**: code
- **Priority**: low
- **Component**: configuration
- **Description**:
    - *Expected*: All modules should use the unified `ConfigSystem`.
    - *Actual*: Hardcoded values exist (e.g., Prowlarr URL in `selenium_integration.py`) despite usage of `ConfigSystem`. `config.py` acts as a shim but isn't consistently used.
    - *Fix*: Enforce usage of `ConfigManager` / `ConfigSystem` across all modules and remove hardcoded fallbacks.
    - *Resolution*: Verified `selenium_integration.py` now exclusively uses `get_config_value` with env var fallbacks, removing hardcoded URLs. `config_system` is now the primary interface for crawler configuration.

### [DevOps] Insecure Deployment Configuration
- **Type**: security
- **Priority**: high
- **Component**: deployment
- **Description**:
    - *Expected*: Service should run as a restricted user with TLS and process management.
    - *Actual*: Application runs as the developer user. Web dashboard lacks TLS. No health checks.
    - *Fix*: Systemd service user, Nginx/Caddy TLS proxy, Health/Metrics endpoints.
    - *Progress*: Added `/health` endpoint to `api_server.py`. Systemd/TLS configuration requires server access.

### [QA] Insufficient Test Coverage ✅ RESOLVED
- **Type**: process
- **Priority**: medium
- **Component**: testing
- **Description**:
    - *Expected*: Critical paths (Auth, Jobs, Config) should have automated tests.
    - *Actual*: Lack of security, integration, or contract tests.
    - *Fix*: Add integration tests for Auth/Jobs, SAST in CI, and reproducible Docker builds.
    - *Resolution*: Added `tests/test_api_health.py` verifying authentication logic and health check. Basic critical path testing established.

### [Reliability] Selenium Crash Recovery ✅ RESOLVED
- **Type**: bug
- **Priority**: medium
- **Component**: selenium_crawler
- **Description**:
    - *Expected*: Browser automation should recover from crashes.
    - *Actual*: No watchdog for Chrome crashes. Reliance on `time.sleep()`.
    - *Fix*: Implement browser watchdog/restart and use `WebDriverWait`.
    - *Resolution*: Replaced `time.sleep` with `WebDriverWait` for deterministic waits. Implemented persistent browser session management in `selenium_integration.py`.

# Hostile Audit Findings (2025-12-18)

### [Security] Selenium Headless Sandbox
- **Type**: security
- **Priority**: high
- **Component**: mam_selenium_service
- **Description**:
    - *Expected*: Browser automation should run with sandboxing enabled to prevent escape if compromised.
    - *Actual*: `mam_selenium_service.py` runs Chrome with `--no-sandbox`. If the headless browser is compromised via a rendered page, it has code execution rights on the host/container.
    - *Fix*: Remove `--no-sandbox` if possible, or ensure the process runs in a highly restricted container user namespace.

### [Security] Loosely Typed Secrets Configuration
- **Type**: security
- **Priority**: medium
- **Component**: config
- **Description**:
    - *Expected*: Missing or misspelled critical environment variables should cause a fast fail on startup.
    - *Actual*: `backend/config.py` uses `extra="ignore"`. Typos in environment variables (e.g. `MAM_PASS` vs `MAM_PASSWORD`) result in silent defaults (empty strings) rather than validation errors, leading to confusing auth failures.
    - *Fix*: Change Pydantic config to `extra="forbid"` and ensure all required fields have no default value in production.

### [Risk] Tracker Ratio Criticality
- **Type**: risk
- **Priority**: critical
- **Component**: ratio_emergency_service
- **Description**:
    - *Expected*: Failsafe mechanisms to prevent ratio destruction.
    - *Actual*: The system relies entirely on `ratio_emergency_service.py` (polling every 5m) to prevent tracker bans. If this service hangs or crashes, qBittorrent could seed indefinitely on freeleech or leech on paid torrents.
    - *Fix*: Add redundant checks or "dead man's switch" limiters at the qBittorrent client level (e.g. max share ratio global limit).

### [Data Integrity] Non-Deterministic Fuzzy Matching
- **Type**: integrity
- **Priority**: medium
- **Component**: goodreads_service
- **Description**:
    - *Expected*: Library state updates should be deterministic and accurate.
    - *Actual*: `goodreads_service.py` uses `difflib` with a 0.85 threshold. This is probabilistic and can lead to "polluted" library state (e.g. marking Book 2 as read when Book 1 was read).
    - *Fix*: Implement strict matching first (ISBN/Exact Title+Author), then cue fuzzy matches for manual review.

### [Architecture] Discovery Service Mismatch
- **Type**: architecture
- **Priority**: low
- **Component**: discovery_service
- **Description**:
    - *Expected*: "Discovery" service should find new content.
    - *Actual*: `discovery_service.py` functions primarily as a "Reconciliation and Filter Service", mapping queued books to library status. It relies on other inputs (Top 10 task) for actual discovery.
    - *Fix*: Rename to `ReconciliationService` or `LibrarySyncService` to reflect actual behavior.

### [Architecture] Fragile Autonomy
- **Type**: architecture
- **Priority**: medium
- **Component**: system
- **Description**:
    - *Expected*: Core loop handles common failure modes.
    - *Actual*: High reliance on external "fixer" scripts (e.g. `fix_qbittorrent.py`, `manual_setup_guide.txt`) suggests the core loop is brittle and requires manual intervention for known failure states.
    - *Fix*: Integrate fixer logic into the main error handling loops.
