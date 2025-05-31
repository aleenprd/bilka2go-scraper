import os
import sys
import json
import asyncio
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter


BASE_URL = "https://www.bilkatogo.dk/"

CATEGORIES_DK = [
    "frugt-og-groent",
    "koed-og-fisk",
    "mejeri-og-koel",
    "drikkevarer",
    "broed-og-kager",
    "kolonial",
    "mad-fra-hele-verden",
    "slik-og-snacks",
    "frost",
    "kiosk",
    "dyremad",
    "husholdning",
    "personlig-pleje",
    "baby-og-boern",
    "bolig-og-koekken",
    "bolig-og-koekken",
    "fritid-og-sport",
    "toej-og-sko",
    "elektronik",
    "have",
    "leg",
    "byggemarked",
    "biludstyr",
]

CATEGORIES_TRANSLATED = {
    "frugt-og-groent": "fruits-and-vegetables",
    "koed-og-fisk": "meat-and-fish",
    "mejeri-og-koel": "dairy-and-chilled",
    "drikkevarer": "beverages",
    "broed-og-kager": "bread-and-cakes",
    "kolonial": "groceries",
    "mad-fra-hele-verden": "world-food",
    "slik-og-snacks": "sweets-and-snacks",
    "frost": "frozen-food",
    "kiosk": "kiosk",
    "dyremad": "pet-food",
    "husholdning": "household",
    "personlig-pleje": "personal-care",
    "baby-og-boern": "baby-and-children",
    "bolig-og-koekken": "home-and-kitchen",
    "fritid-og-sport": "leisure-and-sport",
    "toej-og-sko": "clothing-and-shoes",
    "elektronik": "electronics",
    "have": "garden",
    "leg": "toys",
    "byggemarked": "hardware-store",
    "biludstyr": "car-accessories",
}


# Add a custom JavaScript function to handle the cookie consent dialog
COOKIE_HANDLER_JS = """
() => {
    // Try to find and click the "Kun nødvendige" (Only necessary) button
    const declineButton = document.querySelector('#declineButton') || 
                          document.querySelector('.coi-banner__decline') ||
                          document.querySelector('button[aria-label="Kun nødvendige"]');
                          
    if (declineButton) {
        console.log("Found cookie decline button, clicking it...");
        declineButton.click();
        return true;
    }
    console.log("Cookie decline button not found");
    return false;
}
"""

# Update the LOAD_MORE_JS constant with better targeting
LOAD_MORE_JS = """
() => {
    // Target the specific button using its attributes and text content
    const buttons = Array.from(document.querySelectorAll('button[data-v-a8a600c6].btn.btn-primary.my-3'));
    const loadMoreButton = buttons.find(btn => {
        const spanText = btn.querySelector('span[data-v-a8a600c6]')?.textContent || '';
        return spanText.includes('Indlæs flere');
    });
    
    if (loadMoreButton) {
        console.log("Found 'Indlæs flere' button, clicking it");
        loadMoreButton.click();
        return true;
    }
    
    // Fallback selectors if the specific one doesn't work
    const altButton = document.querySelector('div[data-v-a8a600c6] button.btn.btn-primary.my-3') ||
                     document.querySelector('div.col-10 button.btn.btn-primary.my-3') ||
                     document.querySelector('button.btn.btn-primary.my-3');
                     
    if (altButton && altButton.innerText.includes('Indlæs flere')) {
        console.log("Found 'Indlæs flere' button with fallback selector");
        altButton.click();
        return true;
    }
    
    console.log("Load more button not found");
    return false;
}
"""


async def do_scrape(
    url: str,
    browser_config: BrowserConfig,
    run_config: CrawlerRunConfig,
    format: str = "markdown",
) -> str:
    """
    Asynchronously crawls a URL and returns the markdown content.
    This function uses the AsyncWebCrawler from crawl4ai to fetch the content.

    Parameters
    ----------
    url : str
        The URL to scrape.
    browser_config : BrowserConfig
        Configuration for the web crawler's browser settings.
    run_config : CrawlerRunConfig
        Configuration for the web crawler's run settings.
    format : str, optional
        The format of the output, defaults to "markdown".
        Supported formats are "markdown", "cleaned_html", and "json".

    Returns
    -------
    str
        The markdown content of the scraped page.

    Raises
    ------
    ValueError
        If the format is not supported or if the URL is invalid.

    """
    if format not in [
        "markdown",
        "cleaned_html",
        "json",
        "fit_markdown",
        "raw_markdown",
        "html",
    ]:
        raise ValueError(
            "Unsupported Format: only 'markdown', 'cleaned_html', 'json', 'fit_markdown', "
            "'raw_markdown', and 'html' are supported."
            " Please choose one of these formats."
        )

    if not url.startswith("http"):
        raise ValueError("URL must start with 'http' or 'https'.")

    if not url.endswith("/"):
        url += "/"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Use CacheMode.BYPASS to ensure fresh content is fetched)
        result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            logger.error(f"Crawl failed: {result.error_message}")
            logger.error(f"Status code: {result.status_code}")
            return None

        data = json.loads(result.extracted_content)
        if not data:
            logger.warning("No data extracted from the page.")
            return None
        else:
            # Save the raw JSON data to a file for debugging
            with open("bilkatogo.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Data extracted successfully: {len(data)} items found.")
        
        if format == "html":
            return result.html
        elif format == "cleaned_html":
            return result.cleaned_html
        elif format == "markdown":
            return result.markdown
        elif format == "fit_markdown":
            return result.markdown.fit_markdown
        elif format == "raw_markdown":
            return result.markdown.raw_markdown
        elif format == "json":
            return result.json


def main():
    # logger.add(sys.stderr, level="INFO")
    logger.info("Starting the web scraping process...")

    browser_config = BrowserConfig(
        browser_type="firefox",  # or "chromium" for Chrome
        headless=False,  # Set to False for debugging; True for production
        use_managed_browser=False,
        verbose=True,
        text_mode=False,  # Set to True for text mode (disables images, CSS, etc.)
        java_script_enabled=True,
        user_agent_mode="random",
        viewport_width=2560,
        viewport_height=1440,
        light_mode=False,  # Set to True for light mode (disables features for performance optimization)
    )
    # prune_filter = PruningContentFilter(
    #     threshold=0.5,
    #     threshold_type="fixed",  # or "dynamic"
    #     min_word_threshold=3
    # )
    fit_md_generator = DefaultMarkdownGenerator(
        # content_filter=prune_filter,
        content_source="fit_html",
        options={"ignore_links": False, "ignore_images": True, "ignore_tables": False},
    )
    schema = {
        "name": "Products",
        "baseSelector": ".product-card-container",
        "fields": [
            # Basic product information
            {
                "name": "title",
                "selector": "p.name.text-break",
                "type": "text"
            },
            {
                "name": "description", 
                "selector": "p.description", 
                "type": "text"
            },
            {
                "name": "price",
                "selector": ".product-price__integer",
                "type": "text"
            },
            {
                "name": "productId",
                "selector": "div.product-card",
                "type": "attribute",
                "attribute": "data-productid"
            },
            
            # Product URL
            {
                "name": "productUrl",
                "selector": "a.product-card__link",
                "type": "attribute",
                "attribute": "href"
            },
            
            # Image data
            {
                "name": "imageUrl",
                "selector": "img.product-image",
                "type": "attribute",
                "attribute": "src"
            },
            # Product producer (often in the description)
            {
                "name": "producer",
                "selector": "p.description span:nth-child(1)",
                "type": "text"
            },
            
            # Product quantity/unit info (often in the description)
            {
                "name": "quantity",
                "selector": "p.description span:nth-last-child(2)",
                "type": "text"
            },
            
            # Price per unit (if available)
            {
                "name": "pricePerUnit",
                "selector": "p.description span:nth-last-child(1)",
                "type": "text"
            },
            
            # Labels (if available)
            {
                "name": "label1",
                "selector": "div.m-2.product-labels div:nth-child(1) img",
                "type": "attribute",
                "attribute": "alt"  
            },
            {
                "name": "label2",
                "selector": "div.m-2.product-labels div:nth-child(2) img",
                "type": "attribute",
                "attribute": "alt"  
            },
            {
                "name": "label3",
                "selector": "div.m-2.product-labels div:nth-child(3) img",
                "type": "attribute",
                "attribute": "alt"  
            },

            # Labels (collected as an array)
            # {
            #     "name": "labels",
            #     "selector": "div.label-background",
            #     "type": "attribute",
            #     "attribute": "alt",
            #     "multiple": True  # This makes it return an array of all matches
            # }
        ]
    }
     
    run_cfg = CrawlerRunConfig(
        # markdown_generator=fit_md_generator,
        extraction_strategy=JsonCssExtractionStrategy(schema),
        css_selector="#__layout > div > div.mini-basket-padding.print--no-padding.print--no-margin.white-frame > div > div:nth-child(5)",
        wait_until="domcontentloaded",  # Wait until the DOM is fully loaded
        js_code=f"""
        // Initial wait for page to load
        await new Promise(r => setTimeout(r, 1000)); 
        
        // Try to decline cookies
        const declineFunc = {COOKIE_HANDLER_JS};
        const declined = declineFunc();
        
        // Wait after declining cookies
        await new Promise(r => setTimeout(r, 200)); 
        
        // Function to find the "Load more" button
        function findLoadMoreButton() {{
            // Try the specific selector first
            const buttons = Array.from(document.querySelectorAll('button[data-v-a8a600c6].btn.btn-primary.my-3'));
            const loadMoreButton = buttons.find(btn => {{
                const spanText = btn.querySelector('span[data-v-a8a600c6]')?.textContent || '';
                return spanText.includes('Indlæs flere');
            }});
            
            if (loadMoreButton) return loadMoreButton;
            
            // Fallback selectors
            const altButton = document.querySelector('div[data-v-a8a600c6] button.btn.btn-primary.my-3') ||
                            document.querySelector('div.col-10 button.btn.btn-primary.my-3') ||
                            document.querySelector('button.btn.btn-primary.my-3');
                            
            if (altButton && altButton.innerText.includes('Indlæs flere')) {{
                return altButton;
            }}
            
            return null;
        }}
        
        // Slow scrolling function
        async function slowScroll(step = 250, delay = 200) {{
            const scrollHeight = document.body.scrollHeight;
            let currentPosition = window.scrollY;
            let targetPosition = currentPosition + step;
            
            // Don't scroll past the bottom
            if (targetPosition > scrollHeight) {{
                targetPosition = scrollHeight;
            }}
            
            window.scrollTo(0, targetPosition);
            await new Promise(r => setTimeout(r, delay));
            
            return targetPosition;
        }}
        
        // Just keep clicking the button until there are no more
        async function clickAllLoadMoreButtons() {{
            let clickCount = 0;
            const maxClicks = 50; // Safety limit
            let previousHeight = 0;
            let noChangeCount = 0;
            
            // Initial scroll to make the button visible
            // window.scrollTo(0, document.body.scrollHeight * 0.7);
            await new Promise(r => setTimeout(r, 600));
            
            while (clickCount < maxClicks) {{
                const button = findLoadMoreButton();
                
                if (!button) {{
                    console.log("No 'Indlæs flere' button found");
                    break;
                }}
                
                // Get current height before clicking
                const beforeHeight = document.body.scrollHeight;
                
                // Click the button
                console.log(`Found and clicking 'Indlæs flere' button #${{clickCount + 1}}`);
                button.click();
                clickCount++;
                
                // Wait for new content to load (longer wait)
                await new Promise(r => setTimeout(r, 600));
                
                // Check if page height changed (meaning new content was added)
                const afterHeight = document.body.scrollHeight;
                if (beforeHeight === afterHeight) {{
                    noChangeCount++;
                    console.log(`Warning: Page height didn't change after click ${{clickCount}} (count: ${{noChangeCount}})`);
                    
                    if (noChangeCount >= 3) {{
                        console.log("No content added after 3 consecutive clicks. Stopping.");
                        break;
                    }}
                }} else {{
                    noChangeCount = 0;
                    console.log(`Page height changed from ${{beforeHeight}} to ${{afterHeight}}. New content loaded.`);
                    
                    // Scroll to make the next button visible
                    window.scrollTo(0, afterHeight * 0.8);
                    await new Promise(r => setTimeout(r, 600));
                }}
            }}
            
            console.log(`Finished clicking load more buttons. Total clicks: ${{clickCount}}`);
            return clickCount;
        }}

        // Execute the button clicking
        const totalClicks = await clickAllLoadMoreButtons();
        
        // Slow scrolling implementation
        const totalHeight = document.body.scrollHeight;
        const scrollStep = 300;  // Smaller steps for slower scrolling
        const scrollDelay = 200;  // Longer delay between scrolls (in ms)
        
        let currentPosition = 0;
        
        while (currentPosition < totalHeight) {{
            window.scrollTo(0, currentPosition);
            currentPosition += scrollStep;
            await new Promise(r => setTimeout(r, scrollDelay));
        }}
        
        // Final scroll to ensure we reached the bottom
        window.scrollTo(0, document.body.scrollHeight);
        
        // Wait a bit more after reaching the end of the page
        await new Promise(r => setTimeout(r, 1000)); 
        
        console.log("Scraping complete!");
        """,
        delay_before_return_html=1,
        scan_full_page=True,
        scroll_delay=2,
        remove_overlay_elements=False,
        remove_forms=False,
        simulate_user=False,
        verbose=True,
        process_iframes=False,  # Process iframes to extract content
        magic=False,  # Enable magic mode for advanced scraping features
        cache_mode=CacheMode.BYPASS,  # Use CacheMode.BYPASS to ensure fresh content is fetched
    )

    md = asyncio.run(
        do_scrape(
            url="https://www.bilkatogo.dk/kategori/frugt-og-groent/",
            browser_config=browser_config,
            run_config=run_cfg,
            format="markdown",
        )
    )
    logger.info("Web scraping completed successfully.")

    logger.info("Writing the markdown content to 'bilkatogo.md'...")
    with open("bilkatogo.md", "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
