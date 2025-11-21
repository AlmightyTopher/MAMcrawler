"""Simple page inspector that writes to file"""
import asyncio
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

async def inspect():
    url = "https://mango-mushroom-0d3dde80f.azurestaticapps.net/"
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:body",
            page_timeout=60000
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            # Save HTML
            Path("catalog_cache").mkdir(exist_ok=True)
            with open("catalog_cache/page.html", 'w', encoding='utf-8') as f:
                f.write(result.html)
            
            # Parse and analyze
            soup = BeautifulSoup(result.html, 'lxml')
            
            output = []
            output.append("="*70)
            output.append("PAGE STRUCTURE ANALYSIS")
            output.append("="*70)
            
            # Check for select elements
            selects = soup.find_all('select')
            output.append(f"\nFound {len(selects)} <select> elements")
            for i, select in enumerate(selects):
                output.append(f"\nSelect #{i+1}:")
                output.append(f"  ID: {select.get('id', 'N/A')}")
                output.append(f"  Name: {select.get('name', 'N/A')}")
                output.append(f"  Class: {select.get('class', 'N/A')}")
                options = select.find_all('option')
                output.append(f"  Options: {len(options)}")
                for opt in options[:10]:
                    output.append(f"    - {opt.get_text(strip=True)} (value={opt.get('value', 'N/A')})")
            
            # Check for buttons
            buttons = soup.find_all('button')
            output.append(f"\nFound {len(buttons)} <button> elements")
            for i, btn in enumerate(buttons[:10]):
                output.append(f"  Button #{i+1}: {btn.get_text(strip=True)[:50]}")
            
            # Check for inputs
            inputs = soup.find_all('input')
            output.append(f"\nFound {len(inputs)} <input> elements")
            for i, inp in enumerate(inputs[:10]):
                output.append(f"  Input #{i+1}: type={inp.get('type', 'N/A')}, name={inp.get('name', 'N/A')}")
            
            # Check for divs with data attributes (React/Vue apps)
            data_divs = soup.find_all(['div'], attrs=lambda x: x and any(k.startswith('data-') for k in x.keys()) if x else False)
            output.append(f"\nFound {len(data_divs)} divs with data- attributes")
            
            # Get body text preview
            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)[:500]
                output.append(f"\nBody text preview:\n{text}")
            
            # Write output
            with open("catalog_cache/analysis.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(output))
            
            print("Analysis complete. Check catalog_cache/analysis.txt and catalog_cache/page.html")
        else:
            print(f"Failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(inspect())
