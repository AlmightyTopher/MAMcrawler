"""
Simple debug script to capture raw HTML and analyze why torrent extraction fails
"""
import asyncio
import os
import json
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

async def simple_debug():
    """Simple debug - just capture HTML and basic analysis"""
    
    username = os.getenv('MAM_USERNAME')
    password = os.getenv('MAM_PASSWORD')
    
    if not username or not password:
        print("ERROR: Missing credentials")
        return
    
    print("Starting simple debug...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "auth_success": False,
        "fantasy_results": {},
        "scifi_results": {}
    }
    
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        verbose=False
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Simple login
        print("Logging in...")
        login_result = await crawler.arun(
            url="https://www.myanonamouse.net/login.php",
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                js_code="""
                await new Promise(resolve => setTimeout(resolve, 2000));
                const emailInput = document.querySelector('input[name="email"]');
                const passwordInput = document.querySelector('input[name="password"]');
                if (emailInput && passwordInput) {
                    emailInput.value = '""" + username + """';
                    passwordInput.value = '""" + password + """';
                    const submitBtn = document.querySelector('input[type="submit"]');
                    if (submitBtn) submitBtn.click();
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }
                """,
                wait_for="css:body",
                page_timeout=60000
            )
        )
        
        if login_result.success:
            results["auth_success"] = True
            print("Auth successful")
        else:
            print(f"Auth failed: {login_result.error_message}")
            return results
        
        # Test Fantasy category
        print("Testing Fantasy category...")
        fantasy_url = "https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=41&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true"
        
        fantasy_result = await crawler.arun(
            url=fantasy_url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for="css:body",
                page_timeout=30000
            )
        )
        
        if fantasy_result.success:
            print("Fantasy page loaded")
            
            # Save HTML
            with open('debug_fantasy.html', 'w', encoding='utf-8') as f:
                f.write(fantasy_result.html)
            
            # Basic analysis
            soup = BeautifulSoup(fantasy_result.html, 'lxml')
            
            # Test selectors
            tdr_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
            all_tr = soup.find_all('tr')
            all_links = soup.find_all('a')
            torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in x)
            
            results["fantasy_results"] = {
                "html_length": len(fantasy_result.html),
                "title": soup.find('title').get_text() if soup.find('title') else "No title",
                "tdr_rows_found": len(tdr_rows),
                "all_tr_elements": len(all_tr),
                "all_links": len(all_links),
                "torrent_links": len(torrent_links),
                "sample_tr_ids": [tr.get('id') for tr in all_tr[:5] if tr.get('id')]
            }
            
            print(f"HTML length: {len(fantasy_result.html)}")
            print(f"Title: {results['fantasy_results']['title']}")
            print(f"tdr_ rows: {len(tdr_rows)}")
            print(f"All TR elements: {len(all_tr)}")
            print(f"Torrent links: {len(torrent_links)}")
            print(f"Sample TR IDs: {results['fantasy_results']['sample_tr_ids']}")
            
            # Check for common issues
            page_text = soup.get_text().lower()
            if 'no results' in page_text:
                print("WARNING: 'No results' found on page")
            if 'login required' in page_text:
                print("WARNING: 'Login required' found on page")
            if 'access denied' in page_text:
                print("WARNING: 'Access denied' found on page")
        
        # Wait between tests
        await asyncio.sleep(3)
        
        # Test SciFi category
        print("Testing SciFi category...")
        scifi_url = "https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=47&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true"
        
        scifi_result = await crawler.arun(
            url=scifi_url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for="css:body",
                page_timeout=30000
            )
        )
        
        if scifi_result.success:
            print("SciFi page loaded")
            
            # Save HTML
            with open('debug_scifi.html', 'w', encoding='utf-8') as f:
                f.write(scifi_result.html)
            
            # Basic analysis
            soup = BeautifulSoup(scifi_result.html, 'lxml')
            
            # Test selectors
            tdr_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
            all_tr = soup.find_all('tr')
            all_links = soup.find_all('a')
            torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in x)
            
            results["scifi_results"] = {
                "html_length": len(scifi_result.html),
                "title": soup.find('title').get_text() if soup.find('title') else "No title",
                "tdr_rows_found": len(tdr_rows),
                "all_tr_elements": len(all_tr),
                "all_links": len(all_links),
                "torrent_links": len(torrent_links),
                "sample_tr_ids": [tr.get('id') for tr in all_tr[:5] if tr.get('id')]
            }
            
            print(f"HTML length: {len(scifi_result.html)}")
            print(f"Title: {results['scifi_results']['title']}")
            print(f"tdr_ rows: {len(tdr_rows)}")
            print(f"All TR elements: {len(all_tr)}")
            print(f"Torrent links: {len(torrent_links)}")
            print(f"Sample TR IDs: {results['scifi_results']['sample_tr_ids']}")
            
            # Check for common issues
            page_text = soup.get_text().lower()
            if 'no results' in page_text:
                print("WARNING: 'No results' found on page")
            if 'login required' in page_text:
                print("WARNING: 'Login required' found on page")
            if 'access denied' in page_text:
                print("WARNING: 'Access denied' found on page")
    
    # Save results
    with open('simple_debug_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\nDebug complete. Results saved to simple_debug_results.json")
    print("HTML files saved to debug_fantasy.html and debug_scifi.html")
    
    return results

if __name__ == "__main__":
    asyncio.run(simple_debug())