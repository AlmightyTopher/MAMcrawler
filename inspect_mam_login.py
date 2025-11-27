#!/usr/bin/env python
"""
Inspect MAM login page structure
"""

import undetected_chromedriver as uc
import time

# Launch Chrome to inspect the page
driver = uc.Chrome()
driver.get("https://www.myanonamouse.net/login.php")

# Wait for page to load
time.sleep(3)

# Save the page source
with open('mam_login_page.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)

# Also print key elements
print("Page Title:", driver.title)
print("\nSearching for form inputs...")

# Look for all input elements
inputs = driver.find_elements("tag name", "input")
print(f"Found {len(inputs)} input elements:")
for inp in inputs:
    print(f"  - {inp.get_attribute('name')}: {inp.get_attribute('type')} - ID: {inp.get_attribute('id')}")

# Look for forms
forms = driver.find_elements("tag name", "form")
print(f"\nFound {len(forms)} forms:")
for form in forms:
    print(f"  - {form.get_attribute('name')}: {form.get_attribute('action')}")

# Look for buttons
buttons = driver.find_elements("tag name", "button")
print(f"\nFound {len(buttons)} buttons:")
for btn in buttons:
    print(f"  - {btn.get_text()}: {btn.get_attribute('type')}")

# Look for submit inputs
submits = driver.find_elements("xpath", "//input[@type='submit']")
print(f"\nFound {len(submits)} submit buttons:")
for sub in submits:
    print(f"  - {sub.get_attribute('name')}: {sub.get_attribute('value')}")

print("\nPage saved to mam_login_page.html")
driver.quit()
