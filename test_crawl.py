import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import urllib.parse

async def test_crawl():
    print("Starting crawl test...")
    title = "The Name of the Wind"
    author = "Patrick Rothfuss"
    query = f"{title} {author}"
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.goodreads.com/search?q={encoded_query}"
    
    print(f"URL: {search_url}")
    
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
        user_agent_mode="random",
        viewport={"width": 1280, "height": 720}
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )

    print("Launching browser...")
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=search_url,
            config=run_config
        )

        if not result.success:
            print(f"Crawl failed: {result.error_message}")
            return

        print("Crawl success!")
        print(f"Result URL: {result.url}")
        print(f"HTML length: {len(result.html)}")
        
        if "/book/show/" in result.url:
            print("Landed on book page")
        else:
            print("Landed on search results")

if __name__ == "__main__":
    asyncio.run(test_crawl())
