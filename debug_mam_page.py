"""
Debug script to examine MAM browse page structure after authentication
"""
import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

async def debug_mam_page():
    username = os.getenv('MAM_USERNAME')
    password = os.getenv('MAM_PASSWORD')
    
    if not username or not password:
        print("ERROR: Missing credentials")
        return
    
    print("DEBUG: Debugging MAM browse page structure...")
    
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        verbose=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Login with stealth behavior
        login_url = "https://www.myanonamouse.net/login.php"
        
        js_login = """
        // Wait for page load
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fill form
        const emailInput = document.querySelector('input[name="email"]');
        const passwordInput = document.querySelector('input[name="password"]');
        
        if (emailInput && passwordInput) {
            emailInput.value = '""" + username + """';
            passwordInput.value = '""" + password + """';
            
            // Click submit
            const submitBtn = document.querySelector('input[type="submit"]');
            if (submitBtn) submitBtn.click();
            
            // Wait for redirect
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
        """
        
        # Login
        print("DEBUG: Logging in...")
        result = await crawler.arun(url=login_url, config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_login,
            wait_for="css:body",
            page_timeout=60000,
            screenshot=True
        ))
        
        if not result.success:
            print(f"ERROR: Login failed: {result.error_message}")
            return
        
        print("DEBUG: Login successful")
        
        # Browse Fantasy audiobooks
        fantasy_url = "https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=41&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true"
        
        print("DEBUG: Fetching Fantasy audiobooks...")
        result = await crawler.arun(url=fantasy_url, config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:body",
            page_timeout=30000
        ))
        
        if not result.success:
            print(f"ERROR: Browse failed: {result.error_message}")
            return
        
        print("DEBUG: Browse successful")
        print(f"DEBUG: HTML length: {len(result.html)}")
        
        # Save raw HTML for examination
        with open('debug_mam_fantasy_page.html', 'w', encoding='utf-8') as f:
            f.write(result.html)
        print("DEBUG: Saved raw HTML to debug_mam_fantasy_page.html")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(result.html, 'lxml')
        
        # Look for all table rows
        all_tr = soup.find_all('tr')
        print(f"DEBUG: Total <tr> elements found: {len(all_tr)}")
        
        # Look for rows with id starting with tdr_
        tdr_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
        print(f"DEBUG: tdr_ rows found: {len(tdr_rows)}")
        
        # Look for rows with torrent in class
        torrent_class_rows = soup.find_all('tr', class_=lambda x: x and 'torrent' in x)
        print(f"DEBUG: torrent class rows found: {len(torrent_class_rows)}")
        
        # Look for all links
        all_links = soup.find_all('a')
        print(f"DEBUG: Total links found: {len(all_links)}")
        
        # Look for links to torrent pages
        torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in x)
        print(f"DEBUG: Torrent links found: {len(torrent_links)}")
        
        if torrent_links:
            print("DEBUG: Sample torrent links:")
            for i, link in enumerate(torrent_links[:5]):
                href = link.get('href')
                text = link.get_text(strip=True)[:50]
                print(f"  {i+1}. {text}... -> {href}")
        
        # Check page title and content
        title = soup.find('title')
        if title:
            print(f"DEBUG: Page title: {title.get_text()}")
        
        # Check for error messages
        error_text = soup.get_text()
        if 'no results' in error_text.lower():
            print("WARNING: 'No results' message found on page")
        if 'login' in error_text.lower() and 'required' in error_text.lower():
            print("WARNING: Login required message found")
        if 'not found' in error_text.lower():
            print("WARNING: 'Not found' message found")

if __name__ == "__main__":
    asyncio.run(debug_mam_page())