# AudiobookShelf Workflow - Visual Diagrams & ASCII Charts

**Visual representations of all workflow scenarios**

---

## DIAGRAM 1: 14-Phase Workflow - Success Path

```
┌─────────────────────────────────────────────────────────────────┐
│                  14-PHASE AUDIOBOOK WORKFLOW                     │
│                    SUCCESS EXECUTION PATH                        │
└─────────────────────────────────────────────────────────────────┘

  Phase 1          Phase 2          Phase 3          Phase 4
  ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
  │Library│         │Sci-Fi│         │Fantasy│        │Queue │
  │ Scan │         │Search│         │ Search│        │Books │
  └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
     │                │                │                │
     └────────────────┼────────────────┼────────────────┘
                      │
  Phase 5          Phase 6          Phase 7          Phase 7+
  ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
  │qBit  │         │Monitor│        │Sync  │         │ID3   │
  │Download         │Downld│        │to ABS│         │ Tags │
  └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
     │                │                │                │
     └────────────────┼────────────────┼────────────────┘
                      │
  Phase 8          Phase 8B         Phase 8C         Phase 8D
  ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
  │Sync  │         │Quality│        │Std   │         │Detect│
  │Meta  │         │Check  │        │Meta  │         │Nar   │
  └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
     │                │                │                │
     └────────────────┼────────────────┼────────────────┘
                      │
  Phase 8E         Phase 8F         Phase 9          Phase 10
  ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
  │Pop   │         │Recheck│        │Author│         │Missing│
  │Nar   │         │Qual   │        │Hist  │         │Queue  │
  └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
     │                │                │                │
     └────────────────┼────────────────┼────────────────┘
                      │
  Phase 11         Phase 12
  ┌──────┐         ┌──────┐
  │Report│         │Backup│
  │+(2C) │         │+Rotate
  └──────┘         └──────┘
                      │
                   SUCCESS
                      │
                   COMPLETE
```

---

## DIAGRAM 2: Decision Tree - Critical Path vs Alternative Paths

```
                                START
                                  │
                    ┌─────────────┴─────────────┐
                    │  PHASE 1: LIBRARY SCAN    │
                    └─────────────┬─────────────┘
                                  │
                        ┌─────────┴─────────┐
                        │ Library Found?    │
                    ┌───┴──────────────┬───┘
                    │ NO               │ YES
                    │                  │
                   EXIT           Continue
              (CRITICAL)               │
                                ┌──────┴──────┐
                                │ PHASE 2 & 3 │
                                └──────┬──────┘
                                       │
                            ┌──────────┴──────────┐
                            │ Any Books Found?    │
                        ┌───┴──────────────┬──────┘
                        │ NO               │ YES
                        │                  │
                    Continue          Continue
                    (Warn)                 │
                        │          ┌───────┴───────┐
                        │          │ PHASE 4: QUEUE│
                        │          └───────┬───────┘
                        │                  │
                        │         ┌────────┴────────┐
                        │         │ Torrents Found? │
                        │     ┌───┴──────────┬──────┘
                        │     │ NO           │ YES
                        │     │              │
                        │    EXIT       Continue
                        │  (CRITICAL)       │
                        │     │      ┌──────┴──────┐
                        │     │      │ PHASE 5: Qt │
                        │     │      └──────┬──────┘
                        │     │             │
                        │     │    ┌────────┴────────┐
                        │     │    │ qBit Available? │
                        │     │┌───┴──────────┬──────┘
                        │     ││ NO           │ YES
                        │     ││              │
                        │     │Skip Dl    Download
                        │     │              │
                        │     └──────┬───────┴────┐
                        │            │            │
                        │     ┌──────┴──────┐     │
                        │     │ PHASE 6-12  │     │
                        │     │ (Metadata)  │     │
                        │     └──────┬──────┘     │
                        │            │            │
                        └────────────┼────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │ PHASE 11: REPORT    │
                          └──────────┬──────────┘
                                     │
                          ┌──────────┴──────────┐
                          │ PHASE 12: BACKUP    │
                          └──────────┬──────────┘
                                     │
                                  SUCCESS
```

---

## DIAGRAM 3: Failure Scenarios - Recovery Paths

```
                              WORKFLOW START
                                    │
                          ┌─────────┴─────────┐
                          │ CRITICAL PHASES   │
                    ┌─────┴─────────────────┘
                    │ (1,4,5 - if enabled)
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌─PHASE 1  PHASE 4    PHASE 5
    │  Lib        Torrents   qBit
    │
    ├─FAIL?──→  ┌──────────────┐
    │           │ Can continue?│
    │           └─┬──────────┬─┘
    │             │NO         │YES
    │            EXIT      Skip & Continue
    │             │           │
    │             │      ┌────┘
    │             │      │
    └────────────┬┴──────┴─────────┐
                 │                  │
        ┌────────┴────────┐   ┌──────────────┐
        │ NON-CRITICAL    │   │ PHASES 8-12  │
        │ (6-9,11-12)     │   │ ALWAYS RUN   │
        │                 │   │ (Metadata)   │
        │ PARTIAL FAIL?   │   │              │
        │ ┌──────────────┐│   └──────────┬───┘
        │ │Continue with ││              │
        │ │Available Data││              │
        │ └──────────────┘│              │
        │                 │              │
        └─────────┬───────┘              │
                  │                      │
            ┌─────┴──────┐               │
            │             │              │
        Continue      Generate Report    │
            │             │              │
            │             │              │
        ┌───┴─────────────┴──────────────┴──┐
        │     PHASE 11: FINAL REPORT        │
        │  (includes all available data)    │
        └───┬─────────────────────────────┬─┘
            │                             │
            │ ┌───────────────────────────┘
            │ │
    ┌───────┴─┴───────┐
    │ PHASE 12: BACKUP│
    └───────┬─────────┘
            │
        ┌───┴────┐
        │Success? │
        ├─┬──────┤
        │Y│ │N   │
        │ │ │    │
       OK WARN  SKIP
        │   │    │
        │   └────┴──→ Manual backup recommended
        │
       END
```

---

## DIAGRAM 4: Download Workflow Timeline

```
PHASE 5-6 TIMELINE: qBittorrent Download Monitoring

Start: 2025-11-27 21:00:00
    │
    ├─ 21:06:00 ──→ Phase 5: Add to qBit (10 downloads)
    │                Status: QUEUED
    │
    ├─ 21:10:00 ──→ Progress: 0%
    │
    ├─ 21:30:00 ──→ Progress: 20%
    │                ├─ Book 1: 100% ✓
    │                ├─ Book 2: 50%
    │                └─ Book 3-10: 0-40%
    │
    ├─ 22:00:00 ──→ Progress: 50%
    │                ├─ Books 1-3: 100% ✓
    │                ├─ Books 4-7: 30-70%
    │                └─ Books 8-10: 10-40%
    │
    ├─ 22:30:00 ──→ Progress: 75%
    │                ├─ Books 1-5: 100% ✓
    │                ├─ Books 6-8: 60-90%
    │                └─ Books 9-10: 50%
    │
    ├─ 23:00:00 ──→ Progress: 95%
    │                ├─ Books 1-8: 100% ✓
    │                ├─ Book 9: 99%
    │                └─ Book 10: 95%
    │
    ├─ 23:10:00 ──→ All Complete: 100% ✓
    │                All 10 books ready
    │
    └─ 23:15:00 ──→ Phase 7: Sync to ABS (10 files imported)

TIMEOUT SCENARIO:
    │
    ├─ 21:06:00 ──→ Phase 5: Start
    │
    ├─ 22:00:00 ──→ Progress: 30%
    │
    ├─ 23:00:00 ──→ Progress: 45%
    │
    ├─ 00:00:00 ──→ Progress: 50%
    │
    ├─ 01:00:00 ──→ Progress: 60%
    │
    ├─ 21:06:00 ──→ 24-HOUR TIMEOUT ⏰
    │ +24h            Decision:
    │                 ├─ 7/10 complete
    │                 ├─ 3/10 incomplete
    │                 └─ Continue with 7? YES
    │
    └─ 21:15:00 ──→ Phase 7: Sync 7 available files
                    Incomplete 3 remain for later import
```

---

## DIAGRAM 5: Metadata Enhancement Phases (8-8F) Flow

```
                      PHASE 8: SYNC METADATA
                                │
                    ┌───────────┴───────────┐
                    │  Fetch from ABS API   │
                    │  10 books retrieved   │
                    └───────────┬───────────┘
                                │
                      ┌─────────┴─────────┐
                      │   Authors: 10     │
                      │   Narrators: 2    │
                      └─────────┬─────────┘
                                │
                    ┌───────────┴───────────┐
                    │ PHASE 8B: QUALITY     │
                    │ Baseline Metrics      │
                    │ Author: 100%          │
                    │ Narrator: 20%         │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │ PHASE 8C: STANDARDIZE │
                    │ Format consistency    │
                    │ - Titles normalized   │
                    │ - Authors cleaned     │
                    │ - Genres normalized   │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │ PHASE 8D: DETECT      │
                    │ Pattern matching      │
                    │ Narrators found: 2    │
                    │ (from existing data)  │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │ PHASE 8E: POPULATE    │
                    │ Google Books API      │
                    │ Missing: 8 narrators  │
                    │ 6-pattern matching    │
                    │ Found: 3 narrators    │
                    └───────────┬───────────┘
                                │
                      ┌─────────┴─────────┐
                      │   Authors: 10     │
                      │   Narrators: 5    │
                      │   (2+3 new)       │
                      └─────────┬─────────┘
                                │
                    ┌───────────┴───────────┐
                    │ PHASE 8F: RECHECK     │
                    │ Post-population       │
                    │ Author: 100%          │
                    │ Narrator: 50%         │
                    │ Improvement: +30%     │
                    └───────────┬───────────┘
                                │
                          CONTINUE
```

---

## DIAGRAM 6: User Progress Tracking (Phase 2C)

```
PHASE 11: GENERATE REPORT (with Enhancement 2C)
                            │
            ┌───────────────┴───────────────┐
            │ get_per_user_metrics()        │
            │ (Enhancement 2C)              │
            └───────────────┬───────────────┘
                            │
                ┌───────────┴───────────┐
                │ GET /api/users        │
                │                       │
                │ Users found: 2        │
                │ - Alice               │
                │ - Bob                 │
                └───────────┬───────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
    ┌───┴──────┐                         ┌──────┴────┐
    │   ALICE  │                         │    BOB    │
    └───┬──────┘                         └──────┬────┘
        │                                       │
    ┌───┴──────────────────┐       ┌────────────┴─────────┐
    │ Listening Stats:     │       │ Listening Stats:     │
    │                      │       │                      │
    │ Books completed: 12  │       │ Books completed: 8   │
    │ In progress: 2       │       │ In progress: 1       │
    │ Current: 45%         │       │ Current: 30%         │
    │ Hours: 48.5          │       │ Hours: 32.0          │
    │ Pace: 2.5 bks/week   │       │ Pace: 1.8 bks/week   │
    └───┬──────────────────┘       └────────────┬─────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                ┌───────────┴───────────┐
                │ FINAL REPORT:         │
                │                       │
                │ User Progress Summary:│
                │ - Alice (metrics)     │
                │ - Bob (metrics)       │
                │                       │
                │ Per-user data added   │
                │ to report JSON        │
                └───────────┬───────────┘
                            │
                       CONTINUE
```

---

## DIAGRAM 7: Backup Rotation (Phase 2B)

```
PHASE 12: AUTOMATED BACKUP
                │
    ┌───────────┴───────────┐
    │ Trigger backup API    │
    │ POST /api/admin/backup│
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │ Get backup list       │
    │ GET /api/admin/backups│
    │                       │
    │ 15 backups found:     │
    │ backup_2025-11-27 ✓   │
    │ backup_2025-11-26 ✓   │
    │ backup_2025-11-25 ✓   │
    │ ...                   │
    │ backup_2025-11-13 ✗   │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │ ROTATION POLICY:      │
    │                       │
    │ Daily backups: 7      │
    │ ├─ Keep last 7 days   │
    │ ├─ 2025-11-27 ✓       │
    │ ├─ 2025-11-26 ✓       │
    │ ├─ 2025-11-25 ✓       │
    │ ├─ 2025-11-24 ✓       │
    │ ├─ 2025-11-23 ✓       │
    │ ├─ 2025-11-22 ✓       │
    │ └─ 2025-11-21 ✓       │
    │                       │
    │ Weekly backups: 4     │
    │ ├─ Keep last 4 weeks  │
    │ ├─ 2025-11-20 ✓       │
    │ ├─ 2025-11-13 ✓       │
    │ ├─ 2025-11-06 ✓       │
    │ └─ 2025-10-30 ✓       │
    │                       │
    │ Older backups: DELETE │
    │ ├─ 2025-10-23 ✗       │
    │ ├─ 2025-10-16 ✗       │
    │ └─ ...                │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │ RESULT:               │
    │                       │
    │ Kept: 11 backups      │
    │ Deleted: 4 backups    │
    │ Total space saved     │
    │ Retention verified    │
    └───────────┬───────────┘
                │
             SUCCESS
```

---

## DIAGRAM 8: Error Handling Strategy

```
PHASE EXECUTION
        │
    ┌───┴────┐
    │ Try Op │
    └───┬────┘
        │
    ┌───┴─────────────┐
    │ Outcome?        │
    ├────┬──────┬─────┤
    │    │      │     │
  SUCC TIMEOUT ERR   OTHER
    │    │      │     │
    │    │      │     └─→ Log warning, Continue
    │    │      │
    │    │      └─→ Log error
    │    │          │
    │    │      ┌───┴─────────────┐
    │    │      │ Is CRITICAL?    │
    │    │      ├────┬───────┬────┤
    │    │      │    │       │    │
    │    │      │   YES     NO   MAYBE
    │    │      │    │       │      │
    │    │      │   EXIT  Continue  │
    │    │      │          (warn)   │
    │    │      │                   │
    │    │      └───────┬───────────┘
    │    │              │
    │    └──→ Retry?
    │         │
    │      ┌──┴──┐
    │      │YES  │NO
    │      │     └──→ Handle error above
    │      │
    │      └──→ Retry (up to 3x)
    │          │
    │       Success?
    │       │
    │       ├─ YES → Continue
    │       └─ NO  → Handle as error
    │
    └──→ Continue to next phase
```

---

## DIAGRAM 9: Complete Workflow Status Matrix

```
PHASE EXECUTION STATUS TRACKING
═════════════════════════════════════════════════════════════════

PHASE │ DESCRIPTION      │ STATUS │ CRITICAL │ DATA LOSS RISK
──────┼──────────────────┼────────┼──────────┼─────────────────
1     │ Library Scan     │ ✓ PASS │ CRITICAL │ No (read-only)
2     │ Sci-Fi Search    │ ✓ PASS │ Medium   │ No (read-only)
3     │ Fantasy Search   │ ✓ PASS │ Medium   │ No (read-only)
4     │ Queue Books      │ ✓ PASS │ CRITICAL │ No (read-only)
5     │ qBit Download    │ ✓ PASS │ CRITICAL │ Medium (partial)
6     │ Monitor Downld   │ ✓ PASS │ Medium   │ Low
7     │ Sync to ABS      │ ✓ PASS │ High     │ High (imports)
7+    │ Write ID3 Tags   │ ✓ PASS │ Low      │ Low
8     │ Sync Metadata    │ ✓ PASS │ Low      │ Low
8B    │ Quality Validate │ ✓ PASS │ Low      │ No
8C    │ Standardize      │ ✓ PASS │ Low      │ Low
8D    │ Detect Narrator  │ ✓ PASS │ Low      │ No
8E    │ Populate Nar     │ ✓ PASS │ Low      │ Low
8F    │ Recheck Quality  │ ✓ PASS │ Low      │ No
9     │ Author History   │ ✓ PASS │ Low      │ No
10    │ Missing Queue    │ ✓ PASS │ Low      │ No
11    │ Final Report     │ ✓ PASS │ Low      │ No
12    │ Automated Backup │ ✓ PASS │ High     │ PREVENTS LOSS

LEGEND:
✓ PASS = Execution completed successfully
CRITICAL = Exit immediately if fails
Medium = Continue with warnings
Low = Non-critical, always continue
Read-only = No modifications made
```

---

## DIAGRAM 10: Recovery Decision Matrix

```
FAILURE LOCATION → │ LIBRARY │ SEARCH │ QUEUE │ DOWNLOAD │ SYNC │ METADATA │ BACKUP
─────────────────→┼─────────┼────────┼───────┼──────────┼──────┼──────────┼────────
Can recover?      │ NO      │ WARN   │ NO    │ RETRY    │ SKIP │ CONTINUE │ RETRY
               │  │         │        │       │          │      │          │
Continue?         │ NO      │ YES    │ NO    │ YES(5min)│ YES  │ YES      │ YES
                  │         │        │       │          │      │          │
Impact            │CRITICAL │ MEDIUM │CRITICAL│ MEDIUM   │ HIGH │ MINIMAL  │ HIGH
                  │         │        │       │          │      │          │
Manual action?    │ REQUIRED│ CHECK  │REQUIRED│ WAIT      │CHECK │ OPTIONAL │REQUIRED
                  │         │        │       │          │      │          │
Data loss risk?   │ YES     │ NO     │ YES   │ MEDIUM    │ HIGH │ MINIMAL  │ PREVENTS
```

---

## DIAGRAM 11: Execution Flow with Parallel Operations (Future)

**CURRENT (Sequential)**:
```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5...
Total time: 2.5+ hours
```

**FUTURE (Parallel - Not Yet Implemented)**:
```
                Phase 4
                  │
        ┌─────────┴─────────┐
        │                   │
     Phase 5a            Phase 5b
     (Sci-Fi dl)         (Fantasy dl)
        │                   │
        └─────────┬─────────┘
                  │
              Phase 7

Total time: Reduced by parallel downloads
```

---

## DIAGRAM 12: Idempotency Map

```
IDEMPOTENT PHASES (Safe to re-run multiple times):
┌───────────────────────────────────────────────┐
│ ✓ Phase 1: Library Scan                       │
│ ✓ Phase 2-3: Searches                         │
│ ✓ Phase 4: Queue                              │
│ ✓ Phase 6: Monitor                            │
│ ✓ Phase 7+: ID3 Tags                          │
│ ✓ Phase 8-12: All metadata & backup           │
└───────────────────────────────────────────────┘

POTENTIALLY PROBLEMATIC PHASES:
┌───────────────────────────────────────────────┐
│ ⚠ Phase 5: qBit - Adds torrents multiple      │
│            times if re-run                    │
│            (Use deduplication if available)   │
│                                               │
│ ⚠ Phase 7: ABS Sync - May create duplicate    │
│            books if folder structure changed  │
│            (Manual cleanup may be needed)     │
└───────────────────────────────────────────────┘

RECOMMENDATION:
When re-running after failure, restart from beginning.
Idempotent phases will skip unchanged data.
```

---

**End of Visual Diagrams**

All workflow scenarios represented as ASCII flowcharts and decision trees.
