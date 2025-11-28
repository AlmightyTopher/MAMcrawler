# absToolbox Quick Start Guide

This guide provides practical examples for integrating absToolbox into your MAMcrawler workflow.

## Quick Links

- **Web Interface**: https://abstoolbox.vito0912.de
- **GitHub**: https://github.com/Vito0912/absToolbox
- **Documentation**: See `ABSTOOLBOX_INTEGRATION.md` for complete reference

---

## Use Case 1: Validate Library Quality Before Operations

**Scenario**: You want to check for metadata issues before running automated operations.

**Steps**:

1. **Create validation script** (`scripts/validate_library_quality.py`):
   ```python
   import asyncio
   import os
   from backend.integrations.abstoolbox_client import (
       absToolboxClient,
       QUALITY_RULES_TEMPLATE,
   )

   async def validate():
       abs_url = os.getenv("ABS_URL", "http://localhost:13378")
       abs_token = os.getenv("ABS_TOKEN")

       async with absToolboxClient(abs_url, abs_token) as client:
           # Run validation
           result = await client.validate_metadata_quality(
               QUALITY_RULES_TEMPLATE, dry_run=True
           )

           # Print results
           print(f"\nQuality Validation Results")
           print(f"=" * 80)
           print(f"Items Checked: {result['total_checked']}")
           print(f"Issues Found: {result['issues_count']}")
           print(f"\nTop Issues:")
           for issue in result['invalid_format'][:10]:
               print(f"  - {issue['title']}")
               for problem in issue['issues']:
                   print(f"    * {problem}")

   asyncio.run(validate())
   ```

2. **Run validation**:
   ```bash
   cd C:\Users\dogma\Projects\MAMcrawler
   venv\Scripts\python scripts/validate_library_quality.py
   ```

3. **Review output**: See which books have metadata issues

---

## Use Case 2: Standardize Author Names (Fix Formatting Issues)

**Scenario**: Some authors are stored as "Smith, John" and need to be "John Smith".

**Steps**:

1. **Create standardization script** (`scripts/standardize_authors.py`):
   ```python
   import asyncio
   import os
   from backend.integrations.abstoolbox_client import (
       absToolboxClient,
       STANDARDIZATION_TEMPLATE,
   )

   async def standardize():
       abs_url = os.getenv("ABS_URL", "http://localhost:13378")
       abs_token = os.getenv("ABS_TOKEN")

       async with absToolboxClient(abs_url, abs_token) as client:
           # First run as dry run to preview changes
           print("Running in DRY RUN mode (no changes will be applied)...\n")
           result = await client.standardize_metadata(
               STANDARDIZATION_TEMPLATE, dry_run=True, batch_size=50
           )

           print(f"\nStandardization Preview")
           print(f"=" * 80)
           print(f"Items Processed: {result['items_processed']}")
           print(f"Items That Would Be Updated: {result['items_updated']}")
           print(f"Errors: {len(result['errors'])}")

           if result['changes']:
               print(f"\nSample Changes (first 5):")
               for change in result['changes'][:5]:
                   print(f"\n  Book: {change['title']}")
                   for field, new_value in change['changes'].items():
                       print(f"    {field}: → {new_value}")

           # Ask for confirmation
           confirm = input(
               "\nApply these changes? (type 'yes' to confirm): "
           )
           if confirm.lower() == "yes":
               print("\nApplying changes...")
               result = await client.standardize_metadata(
                   STANDARDIZATION_TEMPLATE, dry_run=False
               )
               print(f"Complete! Updated {result['items_updated']} items")
           else:
               print("Cancelled.")

   asyncio.run(standardize())
   ```

2. **Run with preview first**:
   ```bash
   venv\Scripts\python scripts/standardize_authors.py
   ```

3. **Review changes** and confirm before applying

---

## Use Case 3: Analyze Series Completion for Author

**Scenario**: You want to know which books are missing in an author's series to create a download queue.

**Steps**:

1. **Create series analyzer** (`scripts/analyze_series_completion.py`):
   ```python
   import asyncio
   import os
   import json
   from backend.integrations.abstoolbox_client import absToolboxClient

   async def analyze_series():
       abs_url = os.getenv("ABS_URL", "http://localhost:13378")
       abs_token = os.getenv("ABS_TOKEN")

       # Example authors to analyze
       authors = [
           "Brandon Sanderson",
           "Robert Jordan",
           "George R.R. Martin",
       ]

       async with absToolboxClient(abs_url, abs_token) as client:
           for author in authors:
               print(f"\nAnalyzing {author}...")
               result = await client.complete_author_series(author)

               # Display series breakdown
               if result['series']:
                   print(f"  Series for {author}:")
                   for series_name, books in result['series'].items():
                       print(f"    - {series_name}: {len(books)} books")

   asyncio.run(analyze_series())
   ```

2. **Run analysis**:
   ```bash
   venv\Scripts\python scripts/analyze_series_completion.py
   ```

3. **Review series completion status**

---

## Use Case 4: Create Bulk Operation Template

**Scenario**: Create a reusable template for operations you run regularly.

**Template file** (`templates/bulk_narrator_standardization.yaml`):

```yaml
operation_name: "Standardize All Narrator Names"
description: "Normalize narrator field formatting across library"
author: "MAMcrawler System"
date_created: "2025-11-27"

# Pre-execution checklist
pre_execution_checks:
  - create_backup: true
  - backup_location: "AudiobookShelf Settings > Backups"
  - test_sample: 10
  - review_preview: true

# Operation parameters
parameters:
  batch_size: 100
  max_items_per_run: 500
  delay_between_batches_ms: 1000

# Dry run first
dry_run: true

# Rules to apply
standardization_rules:
  narrator:
    - action: "remove_prefix"
      pattern: "^Narrated by "
    - action: "remove_prefix"
      pattern: "^Narrator: "
    - action: "normalize_whitespace"
      pattern: "\\s{2,}"
      replacement: " "
    - action: "capitalize"
      format: "Title Case"

# Post-execution actions
post_execution:
  - verify_changes: true
  - generate_report: true
  - log_operation: true
  - notify_completion: false

# Rollback plan
rollback:
  available: true
  instructions: "Restore from pre-operation backup"
```

**Usage**:
```bash
# Load and apply template
venv\Scripts\python -c "
from ruamel.yaml import YAML
yaml = YAML()
with open('templates/bulk_narrator_standardization.yaml') as f:
    template = yaml.load(f)
    print(f'Loaded template: {template[\"operation_name\"]}')"
```

---

## Use Case 5: Integrate into MAMcrawler Workflow

**Enhanced Phase 8** in `execute_full_workflow.py`:

```python
# Add to Phase 8 section
async def sync_metadata_with_abstoolbox(self) -> Dict:
    """Phase 8B: Apply absToolbox metadata standardization"""
    self.log("PHASE 8B: METADATA STANDARDIZATION WITH ABSTOOLBOX", "PHASE")

    try:
        from backend.integrations.abstoolbox_client import (
            absToolboxClient,
            QUALITY_RULES_TEMPLATE,
            STANDARDIZATION_TEMPLATE,
        )

        async with absToolboxClient(self.abs_url, self.abs_token) as client:
            # Step 1: Validate quality
            self.log("Validating metadata quality...", "SYNC")
            validation = await client.validate_metadata_quality(
                QUALITY_RULES_TEMPLATE, dry_run=True
            )

            self.log(
                f"Quality check: {validation['issues_count']} issues found",
                "WARN" if validation['issues_count'] > 0 else "OK",
            )

            # Step 2: Standardize if issues found
            if validation['issues_count'] > 0:
                self.log("Applying standardization rules...", "SYNC")
                std_result = await client.standardize_metadata(
                    STANDARDIZATION_TEMPLATE, dry_run=True
                )

                self.log(
                    f"Standardization preview: {std_result['items_updated']} items would be updated",
                    "OK",
                )

            # Step 3: Analyze series completion
            self.log("Analyzing series completion...", "SYNC")
            for author in self.new_authors:
                series_result = await client.complete_author_series(author)
                self.log(
                    f"{author}: {len(series_result['series'])} series",
                    "OK",
                )

            return validation

    except ImportError:
        self.log("absToolbox client not available, skipping enhancement", "WARN")
        return {"skipped": True}
    except Exception as e:
        self.log(f"absToolbox operation error: {e}", "WARN")
        return {"error": str(e)}
```

**Then call it in main execute method**:
```python
# Phase 8: Sync metadata
await self.sync_metadata()

# Phase 8B: Apply absToolbox enhancements
await self.sync_metadata_with_abstoolbox()
```

---

## Common Operations Cheat Sheet

### Check Library Statistics

```python
async with absToolboxClient(abs_url, abs_token) as client:
    stats = await client.get_library_stats()
    print(f"Library: {stats['library_name']}")
    print(f"Total Items: {stats['items']}")
```

### Validate Quality (Dry Run)

```python
result = await client.validate_metadata_quality(
    quality_rules, dry_run=True
)
print(f"Issues found: {result['issues_count']}")
```

### Standardize Metadata (Preview Only)

```python
result = await client.standardize_metadata(
    operation_template, dry_run=True, batch_size=50
)
print(f"Would update: {result['items_updated']} items")
```

### Complete Series Analysis

```python
result = await client.complete_author_series("Brandon Sanderson")
print(f"Series: {len(result['series'])}")
for series_name in result['series']:
    print(f"  - {series_name}")
```

---

## Safety Best Practices

### Before Any Operation

1. **Create Backup**
   - AudiobookShelf: Settings > Backups > Create Backup
   - Note the backup timestamp

2. **Test on Small Sample**
   - Run with `dry_run=True` first
   - Review preview output
   - Only apply to 5-10 items initially

3. **Monitor Execution**
   - Keep server logs visible
   - Watch resource usage
   - Be ready to stop if needed

4. **Verify Results**
   - Check affected books in ABS UI
   - Verify metadata is correct
   - No corruption of files

### After Each Operation

1. **Log Results**
   - Operation ID and timestamp
   - Number of items affected
   - Any errors or warnings

2. **Document Decisions**
   - Why this operation was run
   - What rules were applied
   - Any manual fixes needed

3. **Create Backup**
   - Save post-operation backup
   - Label with operation name
   - Keep for 30 days minimum

---

## Troubleshooting

### Operation Takes Too Long

**Solution**: Reduce `batch_size` parameter
```python
result = await client.standardize_metadata(
    template, dry_run=False, batch_size=25  # Reduced from 50
)
```

### Memory Usage Too High

**Solution**: Add delays between batches
```python
# In implementation, increase the asyncio.sleep delay
await asyncio.sleep(2)  # Increase from 1 second
```

### Changes Not Applied

**Solution**: Verify API token and permissions
```python
# Test connectivity first
stats = await client.get_library_stats()
if stats.get('items') == 0:
    print("Check ABS token and server URL")
```

### Rollback After Bad Operation

**Steps**:
1. Stop any running operations
2. Go to AudiobookShelf: Settings > Backups
3. Click "Restore" on backup created before operation
4. Wait for restore to complete
5. Verify library in ABS UI

---

## Next Steps

1. **Start with validation**: Use `validate_metadata_quality()` to understand issues
2. **Test standardization**: Run in dry-run mode to preview changes
3. **Analyze series**: Use `complete_author_series()` to find missing books
4. **Integrate gradually**: Add operations to workflow one at a time
5. **Document results**: Keep detailed logs of all operations

---

## Resources

- **Full Documentation**: `ABSTOOLBOX_INTEGRATION.md`
- **Client Code**: `backend/integrations/abstoolbox_client.py`
- **Workflow Integration**: `execute_full_workflow.py`
- **GitHub Issues**: https://github.com/Vito0912/absToolbox/issues

