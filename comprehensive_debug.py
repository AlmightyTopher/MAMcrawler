"""
Comprehensive Debug Script - Analyze MAM Page Structure
This script will capture the actual HTML content and analyze why torrent extraction fails.
"""
import asyncio
import os
import json
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

async def debug_mam_structure():
    """Deep analysis of MAM page structure after authentication."""
    
    username = os.getenv('MAM_USERNAME')
    password = os.getenv('MAM_PASSWORD')
    
    if not username or not password:
        print("ERROR: Missing MAM credentials")
        return
    
    print("=" * 80)
    print("COMPREHENSIVE MAM PAGE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "categories_tested": [],
        "authentication_success": False,
        "html_analysis": {},
        "torrent_extraction_attempts": {},
        "errors": []
    }
    
    # Test URLs - Fantasy and SciFi categories
    test_urls = [
        {
            "name": "Fantasy",
            "category_code": "41", 
            "url": "https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=41&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true"
        },
        {
            "name": "Science Fiction",
            "category_code": "47",
            "url": "https://www.myanonamouse.net/tor/browse.php?&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=47&tor[browse_lang][]=1&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true"
        }
    ]
    
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        verbose=False  # Reduce noise
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Login to MAM
        print("Step 1: Authenticating with MyAnonamouse...")
        
        login_js = """
        // Wait for page load
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fill login form
        const emailInput = document.querySelector('input[name="email"]');
        const passwordInput = document.querySelector('input[name="password"]');
        
        if (emailInput && passwordInput) {
            emailInput.value = '""" + username + """';
            passwordInput.value = '""" + password + """';
            
            // Submit form
            const submitBtn = document.querySelector('input[type="submit"]');
            if (submitBtn) {
                submitBtn.click();
                await new Promise(resolve => setTimeout(resolve, 5000));
                return {success: true};
            }
        }
        return {success: false, error: "Form elements not found"};
        """
        
        login_result = await crawler.arun(
            url="https://www.myanonamouse.net/login.php",
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                js_code=login_js,
                wait_for="css:body",
                page_timeout=60000
            )
        )
        
        if login_result.success:
            results["authentication_success"] = True
            print("✓ Authentication successful")
        else:
            results["errors"].append(f"Authentication failed: {login_result.error_message}")
            print(f"✗ Authentication failed: {login_result.error_message}")
            return results
        
        # Step 2: Test each category
        for category_info in test_urls:
            print(f"\nStep 2: Testing {category_info['name']} category...")
            
            category_result = {
                "name": category_info["name"],
                "url": category_info["url"],
                "crawl_success": False,
                "html_saved": False,
                "analysis": {}
            }
            
            try:
                # Fetch the browse page
                crawl_result = await crawler.arun(
                    url=category_info["url"],
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        wait_for="css:body",
                        page_timeout=30000
                    )
                )
                
                if crawl_result.success:
                    category_result["crawl_success"] = True
                    print(f"✓ Browse page loaded successfully")
                    print(f"  HTML length: {len(crawl_result.html)} characters")
                    
                    # Save raw HTML for manual inspection
                    html_filename = f"debug_{category_info['name'].lower().replace(' ', '_')}_page.html"
                    with open(html_filename, 'w', encoding='utf-8') as f:
                        f.write(crawl_result.html)
                    category_result["html_saved"] = html_filename
                    print(f"  HTML saved to: {html_filename}")
                    
                    # Analyze HTML structure
                    soup = BeautifulSoup(crawl_result.html, 'lxml')
                    
                    # Basic page analysis
                    analysis = {
                        "title": soup.find('title').get_text() if soup.find('title') else "No title",
                        "total_tr_elements": len(soup.find_all('tr')),
                        "total_td_elements": len(soup.find_all('td')),
                        "total_a_elements": len(soup.find_all('a')),
                        "all_table_rows": [],
                        "torrent_selectors_tested": {},
                        "potential_torrent_indicators": []
                    }
                    
                    # Test all possible torrent selector patterns
                    selector_patterns = [
                        # Original working pattern
                        ("tdr_ ID pattern", lambda x: x and x.startswith('tdr_')),
                        # Class-based patterns
                        ("torrent class", lambda x: x and 'torrent' in x.lower()),
                        ("row class", lambda x: x and 'row' in x.lower()),
                        # Generic row patterns
                        ("All TR elements", lambda x: True),
                    ]
                    
                    for pattern_name, selector_func in selector_patterns:
                        try:
                            rows = soup.find_all('tr', id=selector_func)
                            analysis["torrent_selectors_tested"][pattern_name] = {
                                "rows_found": len(rows),
                                "sample_ids": [row.get('id', 'NO_ID') for row in rows[:3]]
                            }
                        except Exception as e:
                            analysis["torrent_selectors_tested"][pattern_name] = {
                                "error": str(e)
                            }
                    
                    # Look for potential torrent indicators in the page
                    page_text = soup.get_text().lower()
                    
                    # Common audiobook torrent indicators
                    indicators = [
                        ("no results", "no results" in page_text),
                        ("login required", "login" in page_text and "required" in page_text),
                        ("error message", "error" in page_text),
                        ("access denied", "access denied" in page_text),
                        ("not found", "not found" in page_text),
                        ("empty page", "no torrents" in page_text)
                    ]
                    
                    for indicator_name, found in indicators:
                        if found:
                            analysis["potential_torrent_indicators"].append(indicator_name)
                    
                    # Detailed table structure analysis
                    tables = soup.find_all('table')
                    for i, table in enumerate(tables[:3]):  # Analyze first 3 tables
                        table_info = {
                            "table_index": i,
                            "rows": len(table.find_all('tr')),
                            "classes": table.get('class', []),
                            "id": table.get('id', 'NO_ID')
                        }
                        
                        # Check first few rows for patterns
                        first_rows = table.find_all('tr')[:3]
                        for j, row in enumerate(first_rows):
                            row_info = {
                                "row_index": j,
                                "id": row.get('id', 'NO_ID'),
                                "classes": row.get('class', []),
                                "num_cells": len(row.find_all(['td', 'th']))
                            }
                            
                            # Look for torrent-like content in this row
                            row_text = row.get_text().strip()
                            if len(row_text) > 10:  # Skip empty or minimal rows
                                row_info["sample_text"] = row_text[:100] + "..." if len(row_text) > 100 else row_text
                            
                            table_info[f"row_{j}_info"] = row_info
                        
                        analysis["all_table_rows"].append(table_info)
                    
                    category_result["analysis"] = analysis
                    print(f"  Analysis complete:")
                    print(f"    - Page title: {analysis['title']}")
                    print(f"    - TR elements: {analysis['total_tr_elements']}")
                    print(f"    - TD elements: {analysis['total_td_elements']}")
                    print(f"    - A elements: {analysis['total_a_elements']}")
                    
                    # Report selector results
                    for pattern, result in analysis["torrent_selectors_tested"].items():
                        if result.get("rows_found", 0) > 0:
                            print(f"    ✓ {pattern}: {result['rows_found']} rows")
                        else:
                            print(f"    ✗ {pattern}: 0 rows")
                    
                    if analysis["potential_torrent_indicators"]:
                        print(f"    ⚠ Potential issues: {', '.join(analysis['potential_torrent_indicators'])}")
                    
                else:
                    results["errors"].append(f"Failed to crawl {category_info['name']}: {crawl_result.error_message}")
                    print(f"✗ Failed to crawl: {crawl_result.error_message}")
            
            except Exception as e:
                error_msg = f"Error testing {category_info['name']}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"✗ {error_msg}")
            
            results["categories_tested"].append(category_result)
            
            # Wait between categories
            await asyncio.sleep(3)
    
    # Save comprehensive analysis
    with open('comprehensive_debug_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Results saved to: comprehensive_debug_results.json")
    print(f"HTML files saved to: debug_*_page.html")
    print(f"Authentication success: {results['authentication_success']}")
    print(f"Categories tested: {len(results['categories_tested'])}")
    print(f"Errors encountered: {len(results['errors'])}")
    
    return results

if __name__ == "__main__":
    asyncio.run(debug_mam_structure())