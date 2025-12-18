<objective>
Perform a "Project Megazord Scan" on the MAMcrawler codebase. This is a hyper-intelligent, meta-cognitive audit to identify gaps, bugs, security risks, and UX issues.
</objective>

<context>
Project: MAMcrawler
Type: Python / FastAPI / Audiobook Automation
Path: c:\Users\dogma\Projects\MAMcrawler
Tracking File: BD_TASKS.md (referred to as "Beads")

The project is an audiobook automation platform involving:
- MAM (MyAnonamouse) crawling (stealth/passive)
- qBittorrent integration
- Audiobookshelf integration
- PostgreSQL database
- FastAPI backend
- Frontend dashboard (HTML/CSS)
</context>

<phases>

    <phase name="1. Self-Analysis (Cognitive Loop)">
        - Analyze your own interpretation of this prompt.
        - Identify potential blind spots in auditing a Python-based crawler system.
        - Output a brief validation of your plan.
    </phase>

    <phase name="2. Project Analysis (Technical Deep Dive)">
        - Scan the codebase structure (backend/, mamcrawler/, scripts/).
        - Evaluate:
            - Code logic and architecture (FastAPI routes, services).
            - Dependency consistency (requirements.txt vs imports).
            - Security (hardcoded secrets, rate limiting, correct use of .env).
            - Error handling and logging resilience.
        - Identify technical debt or "code smells" (e.g., duplicated logic, magic numbers).
    </phase>

    <phase name="3. Development Quality Check (Virtual QA)">
        - Simulate the build/run process:
            - Verify `config.py` loads correctly.
            - Check if `alembic` migrations would pass (structure check).
            - Simulate a task execution flow (e.g., `search_books` -> `crawl` -> `download`).
        - Look for edge cases: what happens if MAM is down? If qBittorrent is unauthorized?
    </phase>

    <phase name="4. End-User Simulation">
        - Analyze `dashboard.html` and related templates.
        - Simulate a user journey:
            - "I want to find 'Project Hail Mary'."
            - "I want to check why my download is stalled."
        - Identify UX friction points (missing feedback, confusing navigation).
    </phase>

    <phase name="5. Beads Issue Reporting">
        - For EVERY issue found, append it to `BD_TASKS.md` (or create if missing) using this EXACT format:

        ```markdown
        ### [Title of Issue]
        - **Type**: [bug | improvement | question | task]
        - **Priority**: [high | medium | low]
        - **Component**: [code | UX | docs | infra | test | logic]
        - **Description**:
            - *Expected*: ...
            - *Actual*: ...
            - *Fix*: ...
        ```
    </phase>

</phases>

<requirements>
- Do not stop at the first error; document it and continue scanning.
- Be extremely specific. "Fix error handling" is bad. "Wrap `get_book_metadata` in try/except block to catch TimeoutError" is good.
- Respect the existing `BD_TASKS.md` content; append new issues at the end.
- Assume the user has `windows` OS.
</requirements>

<verification>
- Confirm that `BD_TASKS.md` has been updated with new findings.
- Ensure the report covers logic, security, and UX.
</verification>
