Automated Audio Archival: A Technical Analysis of Heuristic Discovery, Quality Filtering, and Integration Architectures for Private Trackers

1. Introduction to Autonomous Digital Archival

The preservation of digital audio media, particularly spoken-word content such as audiobooks, presents a distinct set of challenges within the domain of data archival. Unlike music, where fidelity is often measured by a linear increase in bitrate (with lossless FLAC being the gold standard), audiobook archival requires a nuanced balance of compression efficiency, narration quality, and structural integrity (e.g., chapterization). Private BitTorrent trackers, specifically MyAnonamouse (MAM), have evolved into the preeminent repositories for this content, maintaining vast libraries of rare and out-of-print materials that are often inaccessible through commercial channels or public indexers. However, the architecture of these "walled gardens" is inherently resistant to the standard automation protocols used in the broader "Arr" stack (Sonarr, Radarr, Readarr).

This report presents a comprehensive technical analysis of a custom automation architecture designed to bridge the gap between the closed ecosystem of MyAnonamouse and the open interoperability of the Prowlarr index management system. The proposed workflow does not merely scrape data; it implements an intelligent agent capable of heuristic decision-making. By leveraging Selenium WebDriver (specifically the stealth-oriented SeleniumBase) for navigation, BeautifulSoup for high-performance parsing, and a custom QualityFilter engine, the system automates the discovery of high-value content based on community signals (seeders) while enforcing rigorous quality control standards (bitrate, narrator, abridgment status).

The necessity for such a system arises from the limitations of existing tools. Standard implementations of Prowlarr or Jackett operate on a "poll-and-match" basis: they wait for a user to request a specific title via an application like Readarr, then search for that exact string. They lack the agency to perform discovery—to browse what is trending, assess the "best" version among dozens of competing encoding standards, and proactively archive the optimal release. This report details the engineering required to build that agency, examining the intricacies of authentication persistence, DOM (Document Object Model) traversal, heuristic scoring algorithms, and API-based integration strategies.

1.1 The Operational Environment: MyAnonamouse (MAM)

MyAnonamouse operates on a codebase that is distinct from the common Gazelle or Unit3d frameworks used by many private trackers. Its interface is heavily reliant on server-side rendering, and while it offers limited API endpoints for specific functions like the "Dynamic Seedbox", it does not expose a comprehensive RESTful API for browsing or searching. This necessitates a "screen scraping" approach, where the automation software must emulate a human user's browser interactions.

The operational environment is further complicated by strict security protocols. Private trackers aggressively monitor for non-human behavior to prevent server strain and data scraping. Standard automation tools like raw Selenium WebDriver are easily fingerprinted and blocked. Therefore, the architectural selection of the browser driver is not merely a preference but a critical stability requirement. The integration of SeleniumBase in UC (Undetected Chromedriver) Mode is pivotal, as it masks the distinct "automation" flags that standard drivers broadcast to the host server.

1.2 Architectural Goals

The primary objective is to create a robust, error-tolerant pipeline that performs the following sequential operations:

1.  **Authentication & Session Management:** Establish and maintain a secure session with MAM, handling cookie persistence and IP registration via the dynamicSeedbox.php endpoint.
2.  **Heuristic Discovery:** Traverse Category 14 (Audiobooks), sorted by seed count, to identify high-demand works.
3.  **Targeted Re-Evaluation:** Isolate the canonical "Title" and "Author" from the discovery phase and execute a targeted deep-search to retrieve all available versions of the work.
4.  **Quality Scoring:** Apply a multi-variable logic gate (The "QualityFilter") to assess candidates based on technical and metadata factors.
5.  **Integration:** Handoff the selected artifact to the local infrastructure via Prowlarr, ensuring seamless ingestion into the download queue.

2. Toolchain Analysis and Selection

The selection of the software stack is dictated by the specific constraints of the target site (MAM) and the integration target (Prowlarr). The architecture decouples the navigation layer from the extraction layer to optimize for both stealth and speed.

2.1 The Navigation Layer: SeleniumBase vs. Standard WebDriver

The foundation of any web automation architecture is the browser driver. In the context of private trackers, "stealth" is the primary metric of success. Standard Selenium WebDriver implementations are inherently noisy. When a standard ChromeDriver is instantiated, it sets the navigator.webdriver property to true, a flag that any basic JavaScript on the target site can read to identify the visitor as a bot. Furthermore, standard drivers often leak consistency checks in the WebGL and Canvas rendering pipelines, which advanced anti-bot systems (like Cloudflare or custom tracker scripts) use for fingerprinting.

To mitigate this, the research identifies SeleniumBase as the superior alternative to a raw Selenium implementation. SeleniumBase is a Python framework that wraps WebDriver but includes specific enhancements for evasion, most notably UC Mode. UC Mode integrates the work of the undetected-chromedriver project, which patches the binary of the ChromeDriver executable to remove the automation flags at the compilation level, rather than just attempting to hide them with JavaScript injections.

| Feature | Standard Selenium WebDriver | SeleniumBase (UC Mode) |
| :--- | :--- | :--- |
| **Navigator Flag** | Reports true (Detected) | Reports false or undefined (Undetected) |
| **Turnstile/CAPTCHA** | Fails or requires manual intervention | Can often bypass automatically |
| **User Agent** | Default generic "Headless" string | Rotates valid, organic User Agents |
| **CDP Access** | Limited | Native integration with Chrome DevTools Protocol |
| **Detection Risk** | High | Low |

For the specific requirement of browsing MAM, which may employ heuristic blocking or simply require a stable, human-like session to maintain account standing, SeleniumBase provides the necessary layer of obfuscation. The script must be configured to run in a headed (visible) mode initially or use xvfb (virtual display) in Linux environments, as "headless" modes are often subjected to stricter scrutiny by server-side security rules.

2.2 The Extraction Layer: BeautifulSoup (BS4)

While Selenium is capable of parsing the DOM using methods like driver.find_element(By.CSS_SELECTOR,...), this approach is computationally inefficient for scraping large datasets (such as a search result page with 50-100 rows). Each call to find_element initiates an Inter-Process Communication (IPC) round-trip between the Python script and the browser driver binary. If the script iterates through 100 rows, extracting Title, Author, Bitrate, and Seeders for each, it generates hundreds of network/IPC calls, resulting in significant latency.

BeautifulSoup (BS4) offers a solution by decoupling parsing from rendering. The architecture dictates that Selenium is used solely to retrieve the page source (driver.page_source). This massive string of HTML is then passed to BS4, which constructs a Python object representing the DOM tree in memory. Using the lxml parser backend, BS4 can traverse this tree, find tags, and extract attributes orders of magnitude faster than Selenium. This separation of concerns allows the automation to be "slow and human" during navigation (to avoid rate limits) but "fast and machine-like" during data processing.

2.3 The Integration Layer: Prowlarr

Prowlarr acts as the central indexer manager in the modern home automation stack. Its primary role is to sync indexer definitions to apps like Sonarr and Radarr. However, for this workflow, we utilize Prowlarr's API as a gateway to the download client. Instead of configuring the Python script with the credentials for qBittorrent or Deluge directly (which decentralizes configuration), the script queries Prowlarr to determine which download client is active and capable of handling torrent/magnet links. This allows the user to change their download client in Prowlarr's UI without needing to update the automation script, adhering to the "Single Source of Truth" principle.

3. Phase 1: Authentication and Session Persistence

The initial phase of the workflow is critical: establishing a valid session with MyAnonamouse. Private trackers typically do not use stateless authentication tokens (like JWTs) for browsing; they rely on session cookies (PHPSESSID, mam_id) tied to the user's IP address.

3.1 Session Rehydration Strategy

To mimic a legitimate user and avoid the "login fatigue" that might flag an account, the automation must implement session persistence. The script should not log in with a username and password on every execution. Instead, it must "rehydrate" a previous session.

1.  **First Run (Initialization):** The script launches SeleniumBase in interactive mode. The user logs in manually, or the script uses type() and click() on the login form elements.
2.  **Cookie Export:** Upon successful login (verified by the presence of a logout button or user profile link), the script extracts all cookies from the driver instance: driver.get_cookies().
3.  **Serialization:** These cookies are serialized (pickled) and stored in a secure local file (e.g., mam_cookies.pkl).
4.  **Subsequent Runs:** The script initializes the driver, navigates to the MAM domain (to set the cookie domain scope), and then injects the stored cookies: driver.add_cookie(cookie_dict).
5.  **Validation:** The script refreshes the page. If the user is logged in, the workflow proceeds. If not (session expired), the script reverts to the login logic.

This approach aligns with the behavior of a standard browser that "remembers" the user, minimizing the footprint on the tracker's authentication servers.

3.2 The Dynamic Seedbox API (dynamicSeedbox.php)

A unique technical constraint of MAM is the "Dynamic Seedbox" system. Downloads (getting the .torrent file) are often restricted to the IP address associated with the active session. If the automation is running on a containerized environment (Docker) or a VPN that rotates IPs, the download request might be rejected even if the session cookies are valid.

MAM provides a specific JSON endpoint to handle this: https://t.myanonamouse.net/json/dynamicSeedbox.php. This endpoint allows a user to register their current IP address as their valid "seedbox" IP for the duration of the session.

**Implementation Details:** The script must perform a GET request to this endpoint using the valid session cookies.

*   **Endpoint:** https://t.myanonamouse.net/json/dynamicSeedbox.php
*   **Headers:** Must include the mam_id cookie.
*   **Response Parsing:** The API returns a JSON object. The script must parse this for {"Success": true}.
    *   **Error Handling:** If the response is {"Success": false, "msg": "No Session Cookie"}, the script knows the session is invalid and must trigger a re-login.

**Integration:** This step should occur immediately after session validation and before any attempts to download files. It effectively "whitelists" the automation's current execution environment.

4. Phase 2: Heuristic Discovery (Browsing Category 14)

With a valid session, the automation proceeds to the discovery phase. The goal is to identify "what is good" without knowing "what to look for." The proxy metric for quality/interest in the BitTorrent ecosystem is "Seeders."

4.1 Constructing the Browse Query

The script navigates to the MAM browse page. To minimize client-side processing, the script leverages the server's sorting engine via URL parameters.

*   **Base URL:** https://www.myanonamouse.net/tor/browse.php
*   **Category Filter:** tor[cat]=14. Category 14 is the designated ID for Audiobooks on MAM.
*   **Sort Parameter:** sort=seeders. This organizes the results table with the highest peer counts at the top.
*   **Order Parameter:** d=DESC (Descending).

This navigation action yields a page containing the 50-100 most active audiobook torrents on the tracker. This list represents the "Zeitgeist" of the community—what users are currently archiving and sharing.

4.2 DOM Structure and Parsing Strategy

Once the page loads, Selenium hands off the page_source to BeautifulSoup. The parsing logic must be robust to handle the varying formatting of tracker tables.

**Table Identification:** The target data resides in a <table> element, typically with a class such as torrents or myBlock. The script must identify this table and iterate over its <tr> (row) children, skipping the header row.

**Row Extraction Logic (Top 10):** The script iterates through the first 10 rows to extract the "Seed" candidates. For each row, the primary datum required is the Title String.

*   **Selector:** row.find('td', class_='torTitle') or similar.
*   **Data:** The text content of this cell usually follows a pattern: Author Name - Book Title (Year) [Format].

4.3 The "Dirty Title" Problem and Regex Cleaning

The raw strings extracted from the browse page are "dirty"—they contain metadata that is useful for the final filter but detrimental to the search phase.

*   **Example:** Andy Weir - Project Hail Mary (Unabridged)
*   **Goal:** Extract Andy Weir and Project Hail Mary.
*   **Regex Solution:** The automation employs a regular expression to parse the string. A robust pattern for MAM (which generally standardizes on Author - Title) is:

    ```regex
    ^(.+?)\s+(?:-|–)\s+(.+?)(?:\s+[\[\(].+)?$
    ```

    *   ^(.+?): Captures the Author (lazy match) at the start.
    *   \s+(?:-|–)\s+: Matches the separator (hyphen or en-dash) surrounded by whitespace.
    *   (.+?): Captures the Title.
    *   (?:\s+[\[\(].+)?$: Non-capturing group that ignores everything starting with ``).

This cleaning process is vital. Searching for "Project Hail Mary" might miss the "Project Hail Mary [MP3]" version that we want to compare it against. By distilling the entry to its atomic metadata (Title + Author), we prepare for the "Deep Search" phase.

5. Phase 3: Targeted Re-Search and Candidate Pooling

A naive automation script would simply download the top result from the "Seeders" list. However, high seeder count often correlates with accessibility (low file size, MP3 format) rather than quality. The user's request for a "QualityFilter" necessitates a second-order operation: the Targeted Re-Search.

5.1 The Re-Search Mechanism

For each of the top 10 identified books, the script executes a new search on MAM.

*   **Query Construction:** query = f"{cleaned_author} {cleaned_title}"
*   **Parameters:** tor[srchIn]={title}. Restricting the search to the title field prevents false positives from descriptions (e.g., "If you liked Project Hail Mary, you'll love this...").
*   **Result:** This search yields a Candidate Pool—a list of all available torrents for that specific book. This pool might include:
    *   A 64kbps MP3 (The one from the high-seeder list).
    *   A 128kbps MP3.
    *   A Chapterized M4B (The likely target).
    *   A FLAC rip (Archival master, huge size).
    *   An Abridged version.

5.2 Deep Metadata Scraper

The script parses this new results page, extracting granular data for every candidate row. This data is mapped to a CandidateRelease object. The extraction rules are complex due to the unstructured nature of the title text.

5.2.1 Bitrate Extraction

Bitrate is rarely in a dedicated column. It is usually a tag in the title.

*   **Regex:** r"(\d+)\s*kbps" or r"\[(\d+)\s*k\]".
*   **Normalization:** The script must convert findings to an integer. If no bitrate is found (common for "Retail" or "Web-DL" tags), the script might look for file size and duration to estimate, or apply a default "Safe" score.

5.2.2 Narrator Extraction

Narrator data is crucial for audiobooks. It is usually embedded in the title string using natural language markers.

*   **Patterns:** "Read by...", "Narrated by...", "With...".
*   **Regex:** r"(?:read|narrated)\s+by\s+([a-zA-Z0-9\s\.]+)" (Case insensitive).
*   **Storage:** The captured name is stored in the narrator attribute of the candidate object.

5.2.3 Abridgment Detection

This is a binary classification based on keyword presence.

*   **Keywords:** Abridged, Unabridged.
*   **Logic:** If Abridged is present, flag as True. If Unabridged is present, flag False. If neither is present, the standard assumption in the audiobook community is Unabridged, but the script might flag it as Unknown for a neutral score.

6. Phase 4: The Heuristic QualityFilter Engine

The core intelligence of the automation lies in the QualityFilter. This is a scoring engine that takes the list of CandidateRelease objects and assigns a numerical QualityScore (QS) to each. The candidate with the highest QS is selected for archival.

6.1 The Bitrate Logic (The "Goldilocks" Curve)

In audio engineering, the relationship between bitrate and perceptual quality is logarithmic, and for spoken word, it differs significantly from music.

*   **< 64 kbps:** Speech can sound "robotic" or have significant artifacts (swishing).
*   **64 kbps:** The industry baseline for mono audiobooks. Acceptable, but not archival.
*   **96 - 128 kbps:** The "Sweet Spot." This range provides near-transparent quality for voice frequencies (85Hz - 255Hz fundamental, up to 8kHz harmonics).
*   **> 192 kbps:** For spoken word, this is generally considered wasted space unless the production involves heavy soundscaping or music.

**Scoring Algorithm:**

*   R = Bitrate
*   If R < 50: QS -= 50 (Penalty for low quality).
*   If 50 <= R < 90: QS += 50 (Baseline).
*   If 90 <= R <= 160: QS += 100 (Target Range).
*   If R > 160: QS += 90 (Slight reduction to prefer efficient encoding over bloat).

6.2 Abridgment Logic

Archival implies preserving the complete work. Abridged versions are treated as "damaged" data.

*   If is_abridged: QS -= 1000 (Disqualifying penalty).
*   If is_unabridged: QS += 100 (Confirmation bonus).

6.3 Narrator Logic

The filter evaluates the narrator field.

*   **Presence Check:** If narrator is not None: QS += 20. This rewards releases where the uploader took the time to include metadata, which serves as a proxy for a higher-effort, higher-quality upload.
*   **Preferred List:** The user may provide a list of "God-Tier" narrators (e.g., Ray Porter, Simon Vance). If narrator in preferred_list: QS += 200.

6.4 Format Logic

Modern audiobook consumption favors the M4B container because it supports internal chapter markers and cover art in a single file, whereas MP3s are often loose collections of files.

*   If format == "M4B": QS += 50.
*   If format == "MP3": QS += 0.

6.5 The Selection Tournament

The script calculates the QS for all candidates.

*   **Tie-Breaking:** If two releases have the same score (e.g., two 128kbps M4B rips), the script falls back to the "Seeders" metric as the tie-breaker, assuming the more seeded one is healthier.
*   **Result:** The release with the highest QS is marked as the Target Artifact.

7. Phase 5: Prowlarr Integration

The final requirement is "Prowlarr Integration." This presents an architectural challenge. Prowlarr is designed as an Indexer Manager (a proxy that exposes indexers via API), not a Download Manager. It typically does not accept "Push" commands for arbitrary magnet links that did not originate from a Prowlarr-initiated search. However, integrating the workflow into the "Arr" ecosystem is critical for the user.

7.1 Integration Strategy: The Client Proxy

The most robust integration method is to use Prowlarr as the Configuration Authority. We do not want to hard-code the qBittorrent IP/Password into our Python script, as this duplicates config. Instead, we query Prowlarr to find out where to send the download.

**Step 1: Fetch Client Config** The script queries Prowlarr's downloadclient endpoint.

*   **Request:** GET http://{prowlarr_host}/api/v1/downloadclient?apikey={apikey}
*   **Response:** A JSON list of configured clients.
*   **Logic:** The script parses this JSON to find the client handling torrent protocols. It extracts the credentials.

**Step 2: The "Grab" Payload** With the credentials and the Target Artifact (Magnet link or Torrent file URL) identified in Phase 4, the script constructs a payload to send to the download client.

*   **Scenario A (Direct Injection):** The script uses the requests library to POST the magnet link directly to the qBittorrent API (using the credentials found in Prowlarr). This effectively "integrates" the result into the Prowlarr-managed infrastructure.
*   **Scenario B (Prowlarr Proxy - Advanced):** If Prowlarr is configured with a specific download client proxy (less common for torrents, common for Usenet), the script might try to POST to api/v1/downloadclient/action/grab. However, documentation suggests this endpoint is reserved for testing or specific actions, not generic downloads.

**Report Recommendation:** The report advocates for Scenario A (Config Retrieval). The script uses Prowlarr as the "Service Registry" to discover the download client, then interacts with the client directly. This satisfies the requirement of "Prowlarr Integration" (using Prowlarr's config data) while bypassing the API limitations regarding foreign GUIDs.

7.2 Category Management

To ensure the download is picked up by the correct management software (e.g., Readarr), the script must apply a Category Tag.

*   **Tag:** audiobooks (or whatever category Readarr monitors).
*   **Mechanism:** When the script POSTs the magnet to the download client, it includes the category parameter.
*   **Outcome:** The download starts. Upon completion, Readarr (monitoring the audiobooks category) sees the completed file, imports it, and organizes it, completing the archival cycle.

8. Implementation Code Logic (Python Structure)

The following structure illustrates the logical flow of the MAM_Archiver class.

```python
class MAM_Archiver:
    def __init__(self):
        # Initialize SeleniumBase with stealth options
        self.sb = SB(uc=True, headless=False)  # Headless=True for production
        self.prowlarr_config = self.get_prowlarr_config()

    def run_workflow(self):
        # Phase 1: Auth
        self.ensure_session()
        self.update_dynamic_seedbox()

        # Phase 2: Browse & Extract
        seeds = self.get_top_seeds()  # Returns list of {'title': '...', 'author': '...'}
        
        for seed in seeds:
            # Phase 3: Targeted Search
            candidates = self.search_candidates(seed)
            
            # Phase 4: Filter
            best_release = self.quality_filter(candidates)
            
            if best_release:
                # Phase 5: Integrate
                self.send_to_downloader(best_release)

    def quality_filter(self, candidates):
        # Implementation of the Heuristic Scoring Engine
        scored_candidates = []
        for c in candidates:
            score = 0
            # Bitrate scoring
            if 64 <= c.bitrate <= 128: score += 100
            elif c.bitrate < 64: score -= 50
            
            # Metadata scoring
            if c.is_unabridged: score += 100
            if c.narrator: score += 20
            
            scored_candidates.append((score, c))
        
        # Sort by score DESC
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates # Return the best candidate object
```

9. Conclusion

The automation of audiobook discovery from MyAnonamouse represents a sophisticated exercise in web scraping and heuristic data analysis. By eschewing the simple "sort and download" approach in favor of a multi-phase "Browse-Search-Filter" workflow, the system moves beyond mere data hoarding to intelligent digital curation. The use of SeleniumBase ensures the longevity of the scraper against anti-bot evolution, while BeautifulSoup provides the necessary speed for processing complex DOM structures. Finally, by integrating with Prowlarr as a configuration authority, the system respects the user's existing infrastructure, creating a seamless pipeline from the "walled garden" of the private tracker to the user's personal media server. This architecture ensures that the archival library is not only large but composed of the highest quality versions available, preserving the cultural value of the audiobooks for the future.
