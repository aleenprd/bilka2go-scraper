import os
import sys
import json
import pytz
import asyncio
import argparse
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from google.cloud import bigquery


load_dotenv()

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

SCHEMA = {
    "name": "Products",
    "baseSelector": ".product-card-container",
    "fields": [
        # Basic product information
        {"name": "title", "selector": "p.name.text-break", "type": "text"},
        {"name": "description", "selector": "p.description", "type": "text"},
        {"name": "price", "selector": ".product-price__integer", "type": "text"},
        {
            "name": "product_id",
            "selector": "div.product-card",
            "type": "attribute",
            "attribute": "data-productid",
        },
        # Product URL
        {
            "name": "product_url",
            "selector": "a.product-card__link",
            "type": "attribute",
            "attribute": "href",
        },
        # Image data
        {
            "name": "image_url",
            "selector": "img.product-image",
            "type": "attribute",
            "attribute": "src",
        },
        # Product producer (often in the description)
        {
            "name": "producer",
            "selector": "p.description span:nth-child(1)",
            "type": "text",
        },
        # Product quantity/unit info (often in the description)
        {
            "name": "quantity",
            "selector": "p.description span:nth-last-child(2)",
            "type": "text",
        },
        # Price per unit (if available)
        {
            "name": "price_per_unit",
            "selector": "p.description span:nth-last-child(1)",
            "type": "text",
        },
        # Labels (if available)
        {
            "name": "label1",
            "selector": "div.m-2.product-labels div:nth-child(1) img",
            "type": "attribute",
            "attribute": "alt",
        },
        {
            "name": "label2",
            "selector": "div.m-2.product-labels div:nth-child(2) img",
            "type": "attribute",
            "attribute": "alt",
        },
        {
            "name": "label3",
            "selector": "div.m-2.product-labels div:nth-child(3) img",
            "type": "attribute",
            "attribute": "alt",
        },
    ],
}


JS_CODE = f"""
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
    """


async def do_scrape(
    url: str,
    browser_config: BrowserConfig,
    run_config: CrawlerRunConfig,
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

    Returns
    -------
    str
        The markdown content of the scraped page.

    Raises
    ------
    ValueError
        If the format is not supported or if the URL is invalid.

    """
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
            logger.error("No data extracted from the page.")
            return None

        logger.info(f"Data extracted successfully: {len(data)} items found.")
        return data


def parse_args():
    """
    Parses command line arguments for the script.

    Returns
    -------
    argparse.Namespace
        The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Web scraping script for BilkaTogo.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode (default: True)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (default: False)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=list(CATEGORIES_TRANSLATED.values()) + ["all"],
        default="all",
        help="Specify a category to scrape (default: all).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Set up logging configuration
    logger.remove()  # Remove the default logger
    logger.add(
        sys.stdout, level=args.log_level.upper(), format="{time} {level} {message}"
    )

    # Set up timezone and job run datetime
    timezone = pytz.timezone("Europe/Copenhagen")
    job_run_datetime = datetime.now(timezone)
    job_run_datetime = job_run_datetime.replace(tzinfo=None)
    job_run_datetime_str = job_run_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    # Connect to BigQuery
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    dataset_name = os.getenv("GOOGLE_CLOUD_BIGQUERY_DATASET")
    bq_client = bigquery.Client(project=project_id)
    dataset_obj = bq_client.dataset(dataset_name)

    # Set up the browser configuration
    browser_config = BrowserConfig(
        browser_type="firefox",  # or "chromium" for Chrome
        headless=True,  # Set to False for debugging; True for production
        use_managed_browser=False,
        verbose=True,
        text_mode=False,  # Set to True for text mode (disables images, CSS, etc.)
        java_script_enabled=True,
        user_agent_mode="random",
        viewport_width=2560,
        viewport_height=1440,
        light_mode=False,  # Set to True for light mode (disables features for performance optimization)
    )

    run_cfg = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(SCHEMA),
        wait_until="domcontentloaded",  # Wait until the DOM is fully loaded
        js_code=JS_CODE,
        delay_before_return_html=1,
        scan_full_page=True,
        scroll_delay=1,
        remove_overlay_elements=False,
        remove_forms=False,
        simulate_user=False,
        verbose=False,
        process_iframes=False,  # Process iframes to extract content
        magic=False,  # Enable magic mode for advanced scraping features
        cache_mode=CacheMode.BYPASS,  # Use CacheMode.BYPASS to ensure fresh content is fetched
    )

    # Scrape each category
    if args.category == "all":
        categories_to_scrape = CATEGORIES_TRANSLATED
    else:
        categories_to_scrape = {
            category: translation
            for category, translation in CATEGORIES_TRANSLATED.items()
            if translation == args.category
        }

    for category, translation in categories_to_scrape.items():
        logger.info(f"Processing category: {category} (translated: {translation})")

        # Create directory and filename for the scraped data
        logger.debug(
            f"Preparing directory and filename for category: {category} (translated: {translation})"
        )
        dir = f"storage/{translation}/"
        filename = f"{dir}{translation}.json"

        if not os.path.exists(dir):
            os.makedirs(dir)

        # Create BigQuery table if it doesn't exist
        table_name = translation.replace("-", "_")
        create_query = f"""
        CREATE OR REPLACE TABLE `{project_id}.{dataset_name}.{table_name}`
        (
            TITLE STRING NOT NULL,
            DESCRIPTION STRING,
            PRICE STRING,
            PRODUCT_ID STRING NOT NULL,
            PRODUCT_URL STRING NOT NULL,
            IMAGE_URL STRING,
            PRODUCER STRING,
            QUANTITY STRING,
            PRICE_PER_UNIT STRING,
            LABEL1 STRING,
            LABEL2 STRING,
            LABEL3 STRING,
            CATEGORY_DK STRING NOT NULL,
            CATEGORY_EN STRING NOT NULL,
            JOB_RUN_DATETIME TIMESTAMP NOT NULL
        );
        """
        logger.info(
            f"Creating table for category: {category} (translated: {translation})"
        )
        logger.info(f"Executing BigQuery create table query: {create_query}")
        query_job = bq_client.query(create_query)
        try:
            # Wait for the query to complete
            query_job.result()
            logger.info(f"Table creation successful for {table_name}")
        except Exception as e:
            raise Exception(f"Error creating table {table_name}: {e}")

        logger.debug(f"Scraping category: {category} (translated: {translation})")
        data = asyncio.run(
            do_scrape(
                url=f"https://www.bilkatogo.dk/kategori/{category}/",
                browser_config=browser_config,
                run_config=run_cfg,
            )
        )

        if not data:
            raise Exception(f"Failed to scrape category: {category}")

        # Add metadata to each product
        logger.info(f"Adding metadata to the scraped data for category: {category}")
        for item in data:
            item["category_dk"] = category
            item["category_en"] = translation
            item["job_run_datetime"] = job_run_datetime_str

        logger.info(f"Writing the result content to '{filename}'...")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # Insert the data into Google BigQuery
        logger.info(f"Inserting data into Bigquery..")
        table_ref = dataset_obj.table(table_name)
        table_obj = bq_client.get_table(table_ref)
        errors = bq_client.insert_rows_json(table_obj, data)

        if errors:
            logger.error(f"Encountered errors while inserting rows: {errors}")
            raise Exception(f"Failed to insert data for category {category}: {errors}")
        else:
            logger.info(
                f"Successfully uploaded {len(data)} rows to BigQuery for category {category}"
            )


if __name__ == "__main__":
    main()
