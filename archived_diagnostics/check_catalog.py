#!/usr/bin/env python
import json

cat = json.load(open('comprehensive_catalog.json'))

authors_to_check = ['Aleron Kong', 'William D. Arand']

for author in authors_to_check:
    print(f"\n{author}:")
    if author in cat:
        for series, data in cat[author].items():
            print(f"  {series}: {data['count']} books")
    else:
        print(f"  NOT FOUND in catalog")
        # Try partial matches
        print(f"  Checking for similar authors...")
        for cat_author in cat.keys():
            if author.lower().split()[0] in cat_author.lower():
                print(f"    Found similar: {cat_author}")
