# Claude Code Strict Behavior Spec

## Autonomous Audiobook + MAM + Prowlarr + qBittorrent Management

You must execute this exact logic. You must not invent new logic. You must not skip steps. All tasks must follow the rules below.

---

### **1. Daily Task + VIP Maintenance Priority**

1. Log into MyAnonamouse (MAM) using stored credentials.
2. Verify download and ratio requirements: `https://www.myanonamouse.net/stats/userBonusPointHistory.php?uid=229756`
3. Check VIP status and point spending options: `https://www.myanonamouse.net/store.php`
4. **VIP Priority Enforcement (Non-Negotiable):**

   * Maintaining VIP status is the highest priority of the entire system.
   * **If VIP is at risk of expiring or dropping below full VIP status:**

     * All point usage must be redirected to VIP renewal or tier maintenance.
     * Do not spend points on audiobook purchases until VIP is secured.
     * Do not download paid audiobooks unless they are freeleech or needed to sustain ratio/VIP.
   * **VIP must always be renewed early**, never allowing expiration risk.
   * **Bonus point surpluses must be spent on VIP as soon as VIP offers maximum possible value.**
5. AFTER VIP is secured and stable:

   * Free audiobooks are second priority.
   * Paid audiobooks are permitted **only when:**

     1. No free or freeleech version meets quality standards.
     2. A paid version is required to meet quality rules in Section 5.
     3. VIP status and point balance remain safe after purchase.
6. If required to purchase a paid FL torrent due to quality enforcement:

   * Ensure post-purchase point balance still supports VIP renewal.
   * If not possible → **do NOT purchase the torrent.**
   * Place title in VIP Pending List to re-check daily until points allow safe purchase.
7. All actions must follow rules scraped from:

   * `https://www.myanonamouse.net/rules.php`
   * `https://www.myanonamouse.net/faq.php`
   * `https://www.myanonamouse.net/f/b/18`
   * `https://www.myanonamouse.net/f/b/78`
   * `https://www.myanonamouse.net/guides/`
   * `https://www.myanonamouse.net/updateNotes.php`
   * `https://www.myanonamouse.net/api/list.php`
8. Newly scraped rule data must always overwrite old rule data. (Run at 12:00 PM)**
9. Log into MyAnonamouse (MAM) using stored credentials.
10. Verify download and ratio requirements on: `https://www.myanonamouse.net/stats/userBonusPointHistory.php?uid=229756`
11. Check VIP status and bonus point usage: `https://www.myanonamouse.net/store.php`
12. Spend bonus points **only when VIP can be maximized** without breaking the rules.
13. All actions must follow rules scraped from these pages including dropdowns and sublinks:

    * `https://www.myanonamouse.net/rules.php`
    * `https://www.myanonamouse.net/faq.php`
    * `https://www.myanonamouse.net/f/b/18`
    * `https://www.myanonamouse.net/f/b/78`
    * `https://www.myanonamouse.net/guides/`
    * `https://www.myanonamouse.net/updateNotes.php`
    * `https://www.myanonamouse.net/api/list.php`
14. Newly scraped rule data must always overwrite old rule data.

---

### **2. Automatic Metadata Scan on First Download**

When a new audiobook appears in Audiobookshelf, perform a **full scan** (Section 14). After scanning, update metadata using verified and Goodreads data.

---

### **3. Weekly Metadata Maintenance**

Once every 7 days, scan and update metadata for all audiobooks **younger than 13 days**. Use the scan + Goodreads process.

---

### **4. Weekly Category Sync (All Audiobook Genres + Focused Top-10 Fantasy & Sci‑Fi)**

1. Log into MAM.
2. Use the provided base URL for MAM searches:

```
https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrentsCATEGORY&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[startDate]=STARTDATE&tor[endDate]=ENDDATE&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true
```

3. Replace CATEGORY using `&tor[cat][]=XX` (XX = category ID without leading “c”).

4. Date format must be `YYYY-MM-DD`.

5. Timespan values:

   * WEEK = today − 7 days
   * MONTH = today − 30 days
   * 3MONTH = today − 90 days
   * 6MONTH = today − 180 days
   * YEAR = today − 365 days
   * ALL = 2008‑01‑01 to today

6. Audiobook Categories (**all must be supported, none may be excluded**):

   * Action/Adventure = 39
   * Art = 49
   * Biographical = 50
   * Business = 83
   * Computer/Internet = 51
   * Crafts = 97
   * Crime/Thriller = 40
   * Fantasy = 41
   * Food = 106
   * General Fiction = 42
   * General Non‑Fic = 52
   * Historical Fiction = 98
   * History = 54
   * Home/Garden = 55
   * Horror = 43
   * Humor = 99
   * Instructional = 84
   * Juvenile = 44
   * Language = 56
   * Literary Classics = 45
   * Math/Science/Tech = 57
   * Medical = 85
   * Mystery = 87
   * Nature = 119
   * Philosophy = 88
   * Pol/Soc/Relig = 58
   * Recreation = 59
   * Romance = 46
   * Science Fiction = 47
   * Self‑Help = 53
   * Travel/Adventure = 89
   * True Crime = 100
   * Urban Fantasy = 108
   * Western = 48
   * Young Adult = 111

7. **Weekly Fantasy & Sci‑Fi Priority Task (STRICT TOP‑10 ENFORCEMENT)**

   * For Fantasy (41) and Science Fiction (47), using WEEK timespan:

     * Sort by `snatchedDesc`.
     * Collect top 10 most‑snatched torrents.
     * Extract title + author for each.
     * Compare to Audiobookshelf.
     * If missing → download via Section 7.
     * After download → scan (Section 14).

**URL Rules (must never change)**

1. Always URL‑encode final link.
2. Never adjust base parameters.
3. Only output final URL.
4. If category missing → refuse output and request one.
5. Log into MAM.
6. For Fantasy (41) and Science Fiction (47):

   * Use the provided base URL + WEEK timespan.
   * Sort by `snatchedDesc`.
   * Retrieve the **top 10**.
7. Extract title + author for each.
8. Compare to Audiobookshelf library.
9. If missing → download via Section 7.
10. After download → scan (Section 14).

**URL Rules (must never change)**

* Always URL-encode the final link.
* Never adjust base parameters.
* Only output final URL.
* If category missing, request one.

---

### **5. Release Quality Rules (Always Apply — Only 1 Best Edition Allowed)**

When multiple releases exist, select **ONLY ONE** version using this priority order. All other releases must be ignored and never downloaded.

1. **Unabridged** over abridged.
2. Highest bitrate available (≥64kbps acceptable; prefer ≥96kbps; ideal 128–192kbps).
3. Prefer **single complete release** unless split has significantly better bitrate.
4. Prefer verified narrator metadata over unknown narrators.
5. Prefer editions without watermarking, branding, or proprietary tagging.
6. Prefer releases with complete chapter/track structure.
7. If two releases are equal in quality → choose the torrent with the highest seeder count.
8. **Do NOT download or keep alternate narrators or editions**, unless required for integrity re-download as defined in Section 13.
9. If a superior edition is discovered after a previous download:

   * Download and replace the inferior version.
   * Run Integrity Check + Scan + Metadata Update.
   * Old inferior version must be removed from the library but remain seeding in qBittorrent if it still generates bonus points.
     When multiple releases exist, select in priority:
10. **Unabridged** over abridged.
11. Highest bitrate available (≥64kbps acceptable; prefer ≥96kbps; ideal 128–192kbps).
12. Prefer **single complete release** unless split has better bitrate.
13. Prefer verified narrator metadata.
14. Prefer no watermark/branding in filenames.
15. Prefer complete chapter structure.
16. If equal → choose highest seeder count.

---

### **6. Event‑Aware Download Rate Adjustments**

Increase wishlist download rate when:

* Freeleech global events occur.
* Bonus/multiplier events run.
* Holiday rewards are announced.
  If no events → slow download pace to avoid violation.

---

### **7. Download Workflow (Prowlarr → MAM Fallback → qBittorrent)**

#### **Primary: Prowlarr**

* Query using title + author + metadata.
* If found → send to qBittorrent.
* Confirm torrent is active.
* After complete → Integrity Check (Section 13) → Scan (Section 14).

#### **Fallback: MAM Download (Free First, Buy If Required)**

If Prowlarr fails, or no acceptable release is found:

1. Log into MAM.
2. Search manually using title + author + series if applicable.
3. Select the release strictly using Section 5 quality rules.

**Free-First Enforcement:**

* If the selected release is **free or freeleech**, you must choose it **before any paid option**, even if paid torrents are available.
* A paid option may only be chosen if **no free/freeleech option exists** that meets Section 5 quality standards.
* You may not choose a paid option to bypass quality rules; free must still pass quality selection.

**If only paid option meets quality rules:**

* Click **Buy as FL**, and confirm **OK**.
* After purchasing, click **Download**.

**If free option meets quality rules but paid options offer higher quality:**

* You must still select the highest-quality paid edition.
* Free is only preferred when equally valid or superior under Section 5.

**Final Mandatory Step:**

* After selecting free or bought-as-FL version, ensure qBittorrent loads the torrent and begins seeding immediately.
  If Prowlarr fails:

1. Search manually via MAM.
2. Apply Release Quality Rules before selecting.
3. If free/freeleech → Download.
4. If not free → click **Buy as FL** → confirm **OK** → Download.
5. Ensure qBittorrent loads and downloads.
6. After complete → Integrity Check (Section 13) → Scan (Section 14).

---

### **8. Series Completion**

1. Determine if audiobook belongs to a series.
2. Identify missing books via Goodreads.
3. Add missing titles to the "Needs Download" list.
4. Download using Section 7.
5. After download → Integrity Check → Scan → Metadata update.

---

### **9. Author & Series Completion (Library-Driven, Genre-Neutral)**

1. Gather complete author list from Audiobookshelf.
2. Gather all known titles by those authors from MAM.
3. Gather all series linked to existing Audiobookshelf titles using scan + Goodreads.
4. Compare against library contents:

   * **Only download missing titles that match:**

     * authors already present in the library
     * or series already present in the library
5. **Genres MUST NOT determine whether a title is downloaded.**

   * Genre data is stored and maintained for search use only.
   * Non-associated genres may NOT trigger library downloads.
6. If few missing titles → download immediately via Section 7.
7. If many missing titles → add to wishlist and download gradually using event-aware pacing (Section 6).
8. All wishlist downloads must follow:

   * Download Workflow (Section 7)
   * Integrity Check (Section 13)
   * Scan (Section 14)
   * Metadata Update (Post-scan)
9. Identify all authors in Audiobookshelf.
10. Scrape full bibliography via MAM.
11. Compare to library contents.
12. If few missing → download immediately.
13. If many → add to wishlist and pull gradually.
14. Follow event-aware scaling (Section 6).
15. All downloaded titles must complete Integrity Check + Scan.

---

### **10. Continuous qBittorrent Monitoring + Weekly Seeder Management + Auto Ratio Emergency System**

**Continuous Monitoring Requirement:**
The system must actively monitor qBittorrent at all times, not just weekly. Monitoring must:

1. Track every torrent’s state (downloading, seeding, paused, stalled, errored).
2. Ensure all completed torrents begin seeding automatically.
3. Restart stalled torrents and retry trackers when needed.
4. Detect ratio conditions and ensure torrents are not paused unless allowed by MAM rules.
5. Never auto-delete torrents unless Section 16 permits their removal.

**Auto Ratio Emergency System (A-Level Protection)**

* The system must **freeze all new paid or non-essential downloads** when the global ratio approaches or drops at/under **1.00**.
* If ratio falls below **1.00**, actions must occur in this order:

  1. **Increase seeding allocation**, raising upload slots and ensuring high-value torrents take priority.
  2. **Force-continue all stalled torrents**.
  3. **Unpause any seeding-capable torrents**, even inferior versions.
  4. **Temporarily block paid FL downloads** unless VIP is at risk.
  5. **Allow only freeleech downloads that increase ratio or benefit VIP.**
* When ratio rises safely above **1.00**, normal download behavior resumes.
* Emergency rules must **never interfere with VIP renewal** (VIP has absolute priority).

**Point Optimization Logic (Always Active):**
The system must maximize MAM Bonus Points by:

* Prioritizing torrents with **active seeders and high demand**.
* Preferring torrents with **low supply/high snatches**, as they generate more points.
* Keeping older, active torrents seeding if they are still producing points.
* Ensuring newly downloaded titles begin seeding immediately to build long-term points.

**Weekly Enforcement:**
Once every 7 days, perform a priority re-evaluation:

1. Categorize torrents by point generation value.
2. Identify torrents that are not generating points.
3. Maintain seeding of high-value torrents indefinitely.
4. Only stop seeding when all of the following are true:

   * Torrent is generating no relevant bonus points.
   * Torrent does not contribute to ratio.
   * Superior edition is actively seeding (if applicable).
   * Removal is allowed by tracker rules.

**Freeleech Point Maximization:**
During global FL, bonus, or multiplier events (Section 6):

* Increase torrent upload slots.
* Increase the number of active seeding torrents.
* Reduce queueing or upload cap to maximize point earning.

**Strict Requirement:**
qBittorrent must never stop seeding, pause seeding, or delete torrents **without explicit rule-based instruction defined in this specification.****
**Continuous Monitoring Requirement:**
The system must actively monitor qBittorrent at all times, not just weekly. Monitoring must:

1. Track every torrent’s state (downloading, seeding, paused, stalled, errored).
2. Ensure all completed torrents begin seeding automatically.
3. Restart stalled torrents and retry trackers when needed.
4. Detect ratio conditions and ensure torrent is not stopped unless allowed by MAM rules.
5. Never auto-delete torrents unless Section 16 permits their removal.

**Point Optimization Logic (Always Active):**
The system must maximize MAM Bonus Points by:

* Prioritizing torrents with **active seeders and high demand**.
* Preferring torrents with **low supply/high snatches**, as they generate more points.
* Keeping older, active torrents seeding if they are still producing points.
* Ensuring newly downloaded titles begin seeding immediately to build long-term points.

**Weekly Enforcement:**
Once every 7 days, perform a priority re-evaluation:

1. Categorize torrents by point generation value.
2. Identify torrents that are not generating points.
3. Maintain seeding of high-value torrents indefinitely.
4. Only stop seeding when all of the following are true:

   * Torrent is generating no relevant bonus points.
   * Torrent does not contribute to ratio.
   * Superior edition is actively seeding (if applicable).
   * Removal is allowed by tracker rules.

**Freeleech Point Maximization:**
During global FL, bonus, or multiplier events (Section 6):

* Increase torrent upload slots.
* Increase the number of active seeding torrents.
* Reduce queueing or upload cap to maximize point earning.

**Strict Requirement

* The system must **never edit or modify `.env` files** under any circumstances.
* All sensitive configurations must be user-supplied manually.
* Any request for such data must provide exact copy/paste instructions for the user.

**Strict Requirement**:**
qBittorrent must never stop seeding, pause seeding, or delete torrents **without explicit rule-based instruction defined in this specification.****

1. Check qBittorrent seeding against MAM needs.
2. Prioritize reseeding torrents that maximize:

   * Bonus points
   * Ratio
   * VIP value
3. Never delete torrents that can still generate points.

---

### **11. Narrator Detection Rules**

Narrator must be recognized using:

1. Speech‑to‑text detection.
2. MAM metadata comparison.
3. Audible narrator scraping (fallback).
4. Fuzzy matching if uncertain.
   Narrator must be stored and used for duplicate filtering and release selection.

---

### **12. Monthly Metadata Drift Correction**

Every 30 days, re-query Goodreads and update:

* Series order
* Cover art
* Description
* Publication info
  Do **not** overwrite:
* Verified scanned title
* Narrator identity

---

### **13. Post‑Download Integrity Check**

After qBittorrent marks complete:

1. Verify file count matches torrent metadata.
2. Verify total size matches torrent.
3. Confirm audio decodes fully.
4. Check duration within 1% tolerance.
5. If failure → re-download, trying alternate release if needed.

---

### **14. Full Scan Definition (All Must Be Done + Duplicate Prevention)**

**Duplicate Prevention Enforcement:**

* During scan, if title/series/author already exists in library:

  * Compare scanned release quality using Section 5.
  * If scanned version is inferior → **abort download and never replace**.
  * If scanned version is superior → **trigger Replacement Procedure (Section 16)**.
* Duplicate narrators are not allowed unless original meets re-download criteria (Section 13).
* Duplicate editions (anniversary/remaster/extended cut) must obey Section 5 and may not be downloaded unless superior.

**Scan Procedure:**

1. Read Audiobookshelf metadata.
2. Read torrent metadata/NFO.
3. Inspect filenames.
4. Perform speech-to-text to detect:

   * Title
   * Series name
   * Series number
   * Author (fuzzy allowed)
   * Narrator
5. Produce canonical metadata:

   * Exact title
   * Exact series + number
   * Best author match
   * Narrator identity
6. Query Goodreads using canonical data.
7. Update Audiobookshelf using Goodreads + narrator data.
8. Apply Duplicate Prevention Rules before saving final metadata.

---

### **15. Metadata Conflict Resolution (Edition/Narrator/Series Conflicts)**

**ENV Protection Rule (System-Wide):**

* The system must **never edit, overwrite, modify, or append** to any `.env` file.
* If credentials, API keys, URLs, or tokens are required:

  * The system must output the **exact key/value lines** required for the user to manually copy/paste.
  * The system must **not assume**, generate placeholder keys, or insert data without user approval.
  * The system must **not proceed with features requiring credentials** until the required values are provided by the user.
* Any attempt to auto-write `.env` values must be treated as a violation and aborted.

**Metadata Conflict Rules:**
When metadata conflicts occur between:

* Torrent metadata
* Speech-to-text information
* Goodreads
* Audiobookshelf (Edition/Narrator/Series Conflicts)**
  When metadata conflicts occur between:
* Torrent metadata
* Speech-to-text information
* Goodreads
* Audiobookshelf

**Resolve conflicts using this strict priority order:**

1. **Scan Speech-to-Text (Title/Series/Sequence Override)**
2. **Goodreads Canonical Data (Title/Series Names + Ordering)**
3. **Narrator from Torrent/Audible + Scan Fuzzy Match**
4. **Torrent Technical Metadata (bitrate, file quality, chapter status)**
5. **Audiobookshelf Existing Metadata (only if fully validated)**

**If conflict persists:**

* Prefer higher bitrate release
* Prefer unabridged
* Prefer verified narrator

**Narrator Conflicts:**

* If narrator differs from existing library:

  * Use Section 5 to decide if current edition must be replaced.
  * If inferior → **trigger Replacement Procedure (Section 16)**.

---

### **16. Explicit Library Replacement Procedure (Mandatory When Superior Edition Found)**

If a newly scanned release is superior to an existing library version:

1. Mark the existing version as **Inferior Edition**.
2. Keep inferior edition **seeding in qBittorrent** if beneficial for points/ratio.
3. Download superior edition using Section 7 rules.
4. Perform Integrity Check (Section 13).
5. Perform Full Scan (Section 14).
6. Update all metadata based on superior edition.
7. Replace files in Audiobookshelf with superior edition.
8. Inferior edition files must be removed from the active library but:

   * **Do NOT stop seeding** unless tracker rules permit or ratio/VIP is unaffected.
9. If inferior edition stops generating benefit:

   * It may be removed **only if the superior edition continues seeding**.

**You must never keep two editions of the same audiobook for listening unless required for MAM seeding.** (All Must Be Done)**

1. Read Audiobookshelf metadata.
2. Read torrent metadata/NFO.
3. Inspect filenames.
4. Perform speech‑to‑text to detect:

   * Title
   * Series name
   * Series number
   * Author (fuzzy allowed)
5. Produce canonical metadata:

   * Exact title
   * Exact series + number
   * Best author match
6. Query Goodreads using canonical data.
7. Update Audiobookshelf using Goodreads + narrator data.

---

### **17. Local Project Documentation + Update Tracking Requirement**

The system must continuously review the local project directory and must not operate blindly. It must:

1. Scan all local source code files, configuration files, API documentation, helper modules, and scripts.
2. Cross‑reference existing project logic with this specification to:

   * Detect missing implementations
   * Detect outdated logic
   * Detect conflicts or deprecated code
3. Monitor and read any documentation stored in:

   * `/docs` or `/documentation` folders
   * `/api` or `/src/api` folders
   * `/config` or configuration directories
   * Root README files or internal docs
4. Identify when new features in this specification require:

   * New files to be created
   * Adjustments to existing logic
   * Additional keys that must be manually added to `.env`

**Update + Change Logging Enforcement:**

* The system must maintain a change log documenting:

  * What logic was updated
  * Why it was updated
  * What file(s) were affected
  * Whether user action is required (e.g., `.env` update)
* Change logs must be output to the user before any new logic goes live.
* The system may not silently apply modifications.

**Silent Update Prohibition

* All modifications to code must be declared, logged, and confirmed via output.
* No changes may occur without explicit logging for the user.

**Mandatory Post-Change Testing + Rollback System**

* After any change is implemented, the system must immediately test the affected components.
* Testing must verify:

  1. Functionality still works as intended.
  2. No regression or broken dependencies occur.
  3. VIP, Ratio, Download, Metadata, and Seeding rules remain functional.
* If testing detects a failure:

  * The change **must be rolled back automatically**.
  * Previous working version must be restored without user input.
  * Change Log must mark the update as **FAILED + ROLLED BACK**.
* If testing passes:

  * The change must be marked as **SUCCESSFUL + ACTIVE**.
* The system is forbidden from deploying untested logic into active use.:**
* All modifications to code must be declared, logged, and confirmed via output.
* No changes may occur without explicit logging for the user.

---

### **19. Mandatory Unit + Integration Testing Requirements**

The system must perform **both unit and integration tests automatically** after any modification.

**Unit Testing Requirements:**

* Must test all internal logic functions individually, including but not limited to:

  * VIP budget + decision logic
  * Free vs paid vs superior edition selection
  * Duplicate prevention & replacement logic
  * Ratio emergency rules & thresholds
  * Metadata parsing, validation, and conflict resolution
  * Narrator detection, fuzzy logic, and prioritization
  * Scan logic and canonical metadata building
* Must confirm expected outputs for multiple test cases per rule.
* Must flag any inconsistency as a test failure.

**Integration Testing Requirements:**

* Must test the entire system interacting with external services:

  * qBittorrent API actions
  * MAM login/session rules
  * Prowlarr querying and fallback behavior
  * MAM scraping + paid/free enforcement
  * Metadata updates across Audiobookshelf
  * Goodreads metadata syncing
  * Event-driven behaviors (Freeleech/Bonus/VIP risk)
* Must simulate and verify end-to-end workflows such as:

  * New download → scan → metadata update → seeding
  * Superior edition replacement
  * Ratio emergency freeze + recovery behavior
  * VIP at-risk handling and purchase restrictions

**Testing Enforcement + Rollback Binding:**

* Both Test Suites (Unit + Integration) must pass **before any code is considered active**.
* If ANY test fails:

  * Cancel deployment
  * Roll back to previous working version automatically
  * Log the change as **FAILED + ROLLBACK ENFORCED**
* If all tests pass:

  * Log change as **SUCCESSFUL + ACTIVE**
  * Apply the change to active runtime

---

### **20. Immutable Specification Enforcement (Gospel Rule Protection)**

This document is **absolute, immutable law** for the system.

* The system must treat this specification as **gospel truth**.
* No rule, definition, process, priority, or behavior described in this document may be altered, removed, or bypassed unless the user explicitly modifies this document.
* The system must store and maintain an internal reference copy of this document.
* Before performing any task, test, or action, the system must:

  1. Validate that its planned behavior aligns with every applicable rule in this document.
  2. Abort any behavior that conflicts with this specification.
  3. Output an error message if it detects a rule violation or unclear instruction.
* The system must continuously check compliance **during execution**, not only before running.
* If a conflict between code and this document is detected:

  * This document overrides the code.
  * Code must be adjusted to re-align with the specification.
  * Update must follow the Change Log + Testing + Rollback requirements (Sections 17–19).

**This specification outranks all code, configs, environment files, documentation, APIs, or user habits.**

---

### **21. ProtonVPN Split Identity Scraping Rules (Immutable + Required)**

#### **21.1 MAM Scraper (Scraper A) Identity = qBittorrent Identity (Hard‑Locked)**

* All MyAnonamouse (MAM) operations must use the **same identity as qBittorrent**, including:

  * Same IP (via ProtonVPN)
  * Same DNS (Proton DNS)
  * Same User Agent (UA)
  * Same client fingerprint expectations
* This identity must be **hard‑coded** and must not rotate or change.
* This identity must use the SOCKS proxy:

  ```
  socks5://127.0.0.1:8080
  ```
* You are forbidden from altering the qBittorrent identity. The scraper must **match it exactly**.

#### **21.2 Metadata Scraper (Scraper B) Identity (Must Never Match A)**

* All non‑MAM scraping (Goodreads, Audible, narrator detection, ISBN lookup, cover art, metadata APIs) must use:

  * Normal WAN IP
  * Local/ISP DNS
  * A different User Agent from Scraper A
* Scraper B must never:

  * Share cookies with Scraper A
  * Share sessions with Scraper A
  * Share headers or UA style with Scraper A
  * Use ProtonVPN or the SOCKS proxy

#### **21.3 Split Tunnel Rules (Windows ProtonVPN v4.3.5)**

* Split Tunnel must be **enabled**.
* Add Scraper A EXE to **Included Apps**.
* Scraper B must **never be included**.
* **Kill Switch must remain OFF** (Split Tunnel conflict).
* Local SOCKS proxy = `127.0.0.1:8080` for Scraper A only.

#### **21.4 Routing Validation (Mandatory Before Any Request)**

Before any scraping or downloading occurs, verify:

| Component            | Expected Identity   |
| -------------------- | ------------------- |
| qBittorrent          | VPN IP + Proton DNS |
| Scraper A (MAM)      | VPN IP + Proton DNS |
| Scraper B (Metadata) | WAN IP + Local DNS  |

If any mismatch is detected:

1. Halt all scraping and downloading.
2. Output correction instructions.
3. Do **not** continue operation until confirmed resolved.

#### **21.5 Timing Requirements for Scraper A (MAM)**

* Delay: **2–5 seconds + jitter** on each request.
* Pause every **20–40 requests** for **2–15 seconds**.
* Retry with **exponential backoff**, never burst retries.

#### **21.6 Security Note (Must Accept & Obey)**

* All non‑MAM traffic **must intentionally leak ISP IP + local DNS**.
* Only MAM traffic must be anonymized.
* This leakage is expected and required under v4.3.5 and must **not** be "fixed".

---

### **22. Partial Fingerprint Mimic Enforcement (Headers Only, No TLS Spoofing)**

* Scraper A (MAM) must share the **same User Agent and IP/DNS identity as qBittorrent**, but must **not attempt deep TLS or network fingerprint spoofing.**
* Scraper A must mimic only **HTTP header identity**, including:

  * User-Agent (hard-locked)
  * Accept / Accept-Encoding
  * Language headers
  * Basic browser-style headers if required by MAM web scraping
* Scraper B (Metadata) must **not** share these header profiles and must generate a separate browser-style identity.
* Scraper B must **never** reuse Scraper A’s:

  * Cookies
  * Sessions
  * Headers
  * User-Agent values
* **TLS fingerprinting and low-level network spoofing are forbidden.** You must not modify TCP options, JA3 signatures, or handshake-level identity.

---

### **23. Token Isolation + Session Separation (Mandatory)**

* Scraper A (MAM identity) and Scraper B (metadata identity) must never share:

  * Login sessions
  * Authentication cookies
  * Session tokens
  * Refresh tokens
  * Persistent login keys
  * Any stored credential artifacts
* Sessions must be created, stored, and refreshed independently for A and B.
* If either scraper accidentally receives credentials belonging to the other, the system must:

  1. Immediately purge and invalidate the token/cookie from memory.
  2. Force that scraper to re-authenticate under its correct identity.
  3. Log the event as a security correction.
* If a token crosses identities (e.g., VPN session token appears on ISP connection or vice‑versa):

  * Halt all scraping and downloading.
  * Clear sessions for the offending scraper.
  * Require re-authentication before continuing.
* Scraper A must not use Scraper B’s headers, UA, or browser profile.
* Scraper B must never use Scraper A’s MAM tokens or cookies, even if they appear valid.

---

### **24. Device Fingerprint Separation (Mandatory Identity Isolation)**

* Scraper A (MAM identity) must present a **minimal, consistent automation-style fingerprint**, matching qBittorrent characteristics wherever possible, without behaving like a full browser.

  * Must not present full browser capabilities (e.g., WebGL, Canvas, WebRTC, high-entropy GPU/Font data).
  * Must not randomize fingerprint between sessions.
  * Must maintain a stable, simple device identity so it appears as a single, predictable automation client.
* Scraper B (Metadata identity) must present a **different fingerprint style**, resembling a normal consumer/browser environment.

  * Must not reuse headers, fonts, capabilities, or similar device traits from Scraper A.
  * May randomize non-essential device traits (within realistic parameters) to avoid repetitive scraping patterns.
* Scraper B must never:

  * Use reduced/automated fingerprints identical to A.
  * Present identical timezone, locale, or canvas/audio fingerprints.
  * Share user agent, hardware hints, or browser profiles.
* If Scraper A and Scraper B fingerprints converge or become suspiciously similar:

  1. Halt scraping for the offending scraper.
  2. Regenerate a new fingerprint appropriate to its identity.
  3. Log the correction event.
* This rule exists to ensure that MAM + qBittorrent appear as one consistent identity, and metadata scraping appears as a separate civilian browser identity.

---

### **25. Behavioral Timing Profiles (Human + Client Emulation)**

* Scraper A (MAM identity) must emulate **client-style polling behavior**, modeled after qBittorrent’s typical frequency and pacing:

  * Fixed but slightly jittered timing intervals between requests.
  * No dramatic timing variance resembling humans.
  * Short, consistent bursts of metadata fetches followed by idle periods.
  * May simulate occasional retry pauses, but must not imitate human scrolling.
* Scraper B (Metadata identity) must emulate **human browsing behavior**, including realistic temporal patterns:

  * Random reading delays (e.g., 1.5s–9s) after page loads.
  * Scroll-like pauses before extracting different elements.
  * Occasional longer pauses (e.g., 10–50s) after multiple requests to mimic real readers.
  * Vary request density by time of day (less activity late at night unless user-specific schedule demands otherwise).
* Behavioral realism must include **subtle variability**, never obvious perfect randomness or fixed timers.
* Neither scraper may adopt the other’s timing pattern. Timing must match the identity:

  * A = predictable client polling
  * B = natural reading + browsing delays
* If scraping is detected as too uniform, too fast, or too robotic:

  1. Adjust timing profile automatically.
  2. Log the adjustment as a behavioral correction event.
  3. Re-test actions under the updated timing model.

---

### **26. Dynamic Anti-Throttle + Anti-Detection Response (Auto Mode)**

* The system must automatically detect elevated risk conditions such as:

  * HTTP 429 (Too Many Requests)
  * Sudden latency spikes from MAM or metadata sites
  * Unexpected HTML/JS behavior that indicates bot-detection
  * CAPTCHA triggers or suspicious redirects
  * Download throttling or anomalous slowdowns
  * HTTP 403/401 pattern shifts linked to fingerprinting or identity issues
* When risk is detected, the system must automatically activate protective actions, including:

  * Reducing request frequency
  * Increasing jitter and random delays
  * Switching to “low‑visibility mode” scraping
  * Extending pauses between tasks
  * Delaying queue processing to a safer future time
* Protective actions must **only enable when risk is detected**. When no risk indicators exist, normal timing rules apply.
* If repeated risk events are detected:

  1. Log the incident as a Risk Event.
  2. Capture limited diagnostic context (without storing personal credentials).
  3. Suggest a timing profile update or manual review.
* Under no circumstances may this system attempt to bypass anti-bot security using malicious tooling (no exploit attempts, no CAPTCHA cracking, no script injection).
* The goal is to **avoid detection, not break detection.**

---

### **27. Hybrid Error + Warning Policy (Strict for Identity/VIP, Soft Elsewhere)**

* The system must enforce a hybrid error model:

  * **STRICT HALT** for threats to:

    * VIP renewal/status
    * Ratio floor (1.00)
    * Identity separation (IP/DNS/UA/session/fingerprint)
    * Token/cookie crossover between Scraper A & B
    * Routing mismatches (VPN vs WAN)
    * Unauthorized attempts to modify `.env`

  * When these issues occur:

    1. Halt all processing
    2. Output a clearly labeled **CRITICAL BLOCK** message
    3. Provide explicit correction instructions
    4. Do not resume until fixed

  * **SOFT-PROTECTION MODE** for low-risk failures such as:

    * Temporary metadata service unavailability (Goodreads/Audible/etc.)
    * Failed narrator matching
    * Bad torrent metadata
    * Timeouts from scraping non-MAM sources
    * API rate limits outside MAM

  * For these, the system must:

    1. Retry using exponential backoff
    2. Pause and automatically re-attempt later
    3. Log a non-critical warning

* **NEVER fail silently.** Every issue must produce either a Warning or a Critical Block.

* **SYSTEM PRIORITY ORDER FOR ERRORS:**

  1. VIP / Ratio / Identity / Security
  2. Torrent Data & Integrity
  3. Metadata completeness

---

### **28. External Source Utilization Policy (Mandatory Documentation Enforcement)**

* The system must reference, extract, and utilize APIs, schemas, and documentation from the following authoritative sources when implementing or modifying features:

**Docker**

* [https://github.com/docker/for-win](https://github.com/docker/for-win)
* [https://github.com/docker/compose](https://github.com/docker/compose)
* [https://github.com/docker/docs](https://github.com/docker/docs)
* [https://github.com/docker/cli](https://github.com/docker/cli)
* [https://github.com/docker/cli-docs-tool](https://github.com/docker/cli-docs-tool)

**Prowlarr**

* [https://github.com/Prowlarr/Prowlarr](https://github.com/Prowlarr/Prowlarr)
* [https://raw.githubusercontent.com/Prowlarr/Prowlarr/develop/src/Prowlarr.Api.V1/openapi.json](https://raw.githubusercontent.com/Prowlarr/Prowlarr/develop/src/Prowlarr.Api.V1/openapi.json)

**Hardcover / Library Sync Tools**

* [https://github.com/hardcoverapp/hardcover-docs](https://github.com/hardcoverapp/hardcover-docs)
* [https://github.com/drallgood/audiobookshelf-hardcover-sync](https://github.com/drallgood/audiobookshelf-hardcover-sync)
* [https://github.com/rohit-purandare/ShelfBridge](https://github.com/rohit-purandare/ShelfBridge)

**LazyLibrarian**

* [https://github.com/lazylibrarian/LazyLibrarian](https://github.com/lazylibrarian/LazyLibrarian)

**Cloudflare**

* [https://github.com/cloudflare/cloudflared](https://github.com/cloudflare/cloudflared)
* [https://github.com/cloudflare/cloudflare-docs](https://github.com/cloudflare/cloudflare-docs)

**qBittorrent**

* [https://github.com/qbittorrent/qBittorrent](https://github.com/qbittorrent/qBittorrent)
* [https://github.com/qbittorrent/qBittorrent-website](https://github.com/qbittorrent/qBittorrent-website)
* [https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0)](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-%28qBittorrent-5.0%29)

**Audiobookshelf**

* [https://github.com/AlmightyTopher/audiobookshelf-api-docs/tree/claude/update-api-docs-01TPDQwZ88iiSSRRYCPbewCS](https://github.com/AlmightyTopher/audiobookshelf-api-docs/tree/claude/update-api-docs-01TPDQwZ88iiSSRRYCPbewCS)
* [https://github.com/audiobookshelf/audiobookshelf-web](https://github.com/audiobookshelf/audiobookshelf-web)
* [https://github.com/advplyr/audiobookshelf](https://github.com/advplyr/audiobookshelf)
* [https://github.com/advplyr/audiobookshelf/blob/master/readme.md](https://github.com/advplyr/audiobookshelf/blob/master/readme.md)

**Required Behavior:**

* Claude must reference these sources when adding or modifying features that interact with them.
* When specifications are missing or ambiguous, Claude must **scrape or clone the referenced documentation or schema** and derive logic from it.
* All API usage must match the exact documented behavior from these sources.
* The system must **not invent or guess API behavior.** It must defer to the documented sources.
* If documentation conflicts with this spec, **this spec overrides functionality, but the documentation must still be followed in all compatible areas.**

---

### **29. WireGuard Configuration Enforcement (VPN Identity Integrity)**

* When configuring system-level VPN behavior, the system must correctly configure **WireGuard** for tunneling traffic from qBittorrent and Scraper A (MAM identity) only.
* Required behavior:

  * WireGuard must route:

    * qBittorrent
    * Scraper A (MAM operations)
  * WireGuard must **not** route:

    * Scraper B (metadata identity)
    * System update checks
    * Documentation/API scraping not related to MAM
* WireGuard must:

  * Use a configured, persistent peer key for the tunnel.
  * Preserve DNS override to the VPN DNS (Proton DNS equivalent) only for routed applications.
  * Never reroute ALL traffic through WireGuard unless explicitly demanded by MAM identity monitoring.
  * Respect `.env` protection: **WireGuard keys must never be written, modified, or generated by the automation.**
* Required user interaction:

  * If WireGuard keys or peer settings are missing, the system must output the required key/value configuration only.
  * The user must copy/paste keys manually.
* Forbidden behaviors:

  * The system must not modify or write any WireGuard configuration files directly.
  * The system must not expose, echo, log, or store private keys.
  * The system must not alter DNS outside the WireGuard routing scope.

**If WireGuard routing does not match identity rules:**

1. Halt all MAM operations immediately.
2. Output a **CRITICAL BLOCK** notice.
3. Provide a remediation checklist.
4. Resume only after confirmation.

---

### **30. Verified Migration Import Block (DO NOT MODIFY)**

* The file `backend/migrations/env.py` contains a verified correct import block and must not be changed under any circumstances.
* The following block is correct as-is:

```
from backend.models import (
    ApiLog,
    Author,
    Book,
    Series,
    Download,
    FailedAttempt,
    MissingBook,
    MetadataCorrection,
    GenreSetting,
    Task,
)
```

**Requirements:**

* Never modify, regenerate, or reformat this import block.
* Never propose changes to it.
* Never attempt automatic migrations that alter these imports.
* Claude must acknowledge this block as correct and uneditable.

**Branch Handling:**

* Claude must proceed with review and merge operations for the branch:

  * `claude/detect-missing-books-017jTmJKaYSE2EZ3DJKGggLN`
* This branch must be processed without altering the verified block.

---

### **31. Rule Obedience Requirement**************************

You must obey all sections. You are forbidden from modifying or ignoring any rule.

### **Visualization Notice (Non-Functional Asset)**

Visualization assets (e.g., PNG/SVG workflow maps) are optional and are not part of the automation logic. They must never influence, alter, or be required by the system.
