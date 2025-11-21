"""
Debug script to inspect the audiobook catalog page structure
"""
import asyncio
import logging
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def inspect_page():
    """Inspect the page structure to understand what elements are available."""
    
    url = "https://mango-mushroom-0d3dde80f.azurestaticapps.net/"
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:body",
            page_timeout=60000,
            screenshot=True
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            logger.info("✅ Page loaded successfully")
            
            # Parse HTML
            soup = BeautifulSoup(result.html, 'lxml')
            
            # Save full HTML for inspection
            html_file = Path("catalog_cache/page_full.html")
            html_file.parent.mkdir(exist_ok=True)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(result.html)
            logger.info(f"📄 Full HTML saved to {html_file}")
            
            # Analyze structure
            print("\n" + "="*70)
            print("PAGE STRUCTURE ANALYSIS")
            print("="*70)
            
            # Check for select elements
            selects = soup.find_all('select')
            print(f"\n📋 Found {len(selects)} <select> elements:")
            for i, select in enumerate(selects):
                print(f"\n  Select #{i+1}:")
                print(f"    - ID: {select.get('id', 'N/A')}")
                print(f"    - Name: {select.get('name', 'N/A')}")
                print(f"    - Class: {select.get('class', 'N/A')}")
                options = select.find_all('option')
                print(f"    - Options: {len(options)}")
                if options:
                    print(f"    - First 5 options:")
                    for opt in options[:5]:
                        print(f"      • {opt.get_text(strip=True)} (value={opt.get('value', 'N/A')})")
            
            # Check for input elements
            inputs = soup.find_all('input')
            print(f"\n📝 Found {len(inputs)} <input> elements:")
            for i, inp in enumerate(inputs[:10]):  # Show first 10
                print(f"  Input #{i+1}: type={inp.get('type', 'N/A')}, name={inp.get('name', 'N/A')}, id={inp.get('id', 'N/A')}")
            
            # Check for buttons
            buttons = soup.find_all('button')
            print(f"\n🔘 Found {len(buttons)} <button> elements:")
            for i, btn in enumerate(buttons[:10]):  # Show first 10
                print(f"  Button #{i+1}: {btn.get_text(strip=True)[:50]} (class={btn.get('class', 'N/A')})")
            
            # Check for forms
            forms = soup.find_all('form')
            print(f"\n📋 Found {len(forms)} <form> elements:")
            for i, form in enumerate(forms):
                print(f"  Form #{i+1}: action={form.get('action', 'N/A')}, method={form.get('method', 'N/A')}")
            
            # Check for divs with filter-related classes/ids
            filter_divs = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['filter', 'search', 'genre', 'category']
            ))
            print(f"\n🔍 Found {len(filter_divs)} filter-related divs:")
            for i, div in enumerate(filter_divs[:5]):
                print(f"  Div #{i+1}: class={div.get('class', 'N/A')}, id={div.get('id', 'N/A')}")
            
            # Check for any React/Vue app containers
            app_containers = soup.find_all(['div'], id=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['app', 'root', 'main']
            ))
            print(f"\n⚛️  Found {len(app_containers)} app container divs:")
            for i, div in enumerate(app_containers):
                print(f"  Container #{i+1}: id={div.get('id', 'N/A')}, class={div.get('class', 'N/A')}")
            
            # Check for script tags (might be a SPA)
            scripts = soup.find_all('script', src=True)
            print(f"\n📜 Found {len(scripts)} external scripts:")
            for i, script in enumerate(scripts[:5]):
                src = script.get('src', '')
                print(f"  Script #{i+1}: {src[:80]}")
            
            # Extract text content preview
            body = soup.find('body')
            if body:
                text_content = body.get_text(separator=' ', strip=True)[:500]
                print(f"\n📝 Body text preview (first 500 chars):")
                print(f"  {text_content}")
            
            print("\n" + "="*70)
            print("✅ Analysis complete. Check catalog_cache/page_full.html for details")
            print("="*70)
            
        else:
            logger.error(f"❌ Failed to load page: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(inspect_page())
