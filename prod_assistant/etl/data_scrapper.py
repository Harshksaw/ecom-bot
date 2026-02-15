import csv
import time
import re
import os
import random
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
import shutil

# --- Anti-detection: User-Agent rotation pool ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

# --- Anti-detection: JS stealth script to mask automation ---
STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
"""


class AmazonScraper:

    def __init__(self, output_dir="data"):  # FIX: was "init"
        self.output_dir = output_dir
        self.debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.debug_dir, exist_ok=True)

    def save_screenshot(self, driver, name):
        """Save a screenshot for debugging."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = os.path.join(self.debug_dir, filename)
        try:
            driver.save_screenshot(path)
            print(f"Screenshot saved to {path}")
            return path
        except Exception as e:
            print(f"Failed to save screenshot: {e}")
            return None

    def _get_driver(self):  # FIX: renamed from "getdriver" to "_get_driver" for consistency
        """Initialize and return a Chrome driver (local or remote)."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # Anti-detection: rotate user-agent on every driver creation
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        # Anti-detection: disable automation info bars
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")

        system_browser_path = None
        system_driver_path = None

        possible_browser_paths = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
        ]
        possible_driver_paths = [
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            "/usr/bin/chromedriver",
            "/usr/bin/chromium-driver",
        ]

        for path in possible_browser_paths:
            if os.path.exists(path):
                system_browser_path = path
                break

        for path in possible_driver_paths:
            if os.path.exists(path):
                system_driver_path = path
                break

        if system_browser_path:
            options.binary_location = system_browser_path

        try:
            if system_driver_path:
                print(f"Using system driver at: {system_driver_path}")
                writable_driver_path = os.path.join(os.getcwd(), "chromedriver_copy")
                try:
                    shutil.copy2(system_driver_path, writable_driver_path)
                    os.chmod(writable_driver_path, 0o755)
                    print(f"Copied driver to: {writable_driver_path}")
                    driver = uc.Chrome(
                        options=options,
                        driver_executable_path=writable_driver_path,
                        use_subprocess=True,
                    )
                    self._apply_stealth(driver)
                    return driver
                except Exception as e:
                    print(f"Failed to copy/patch driver, trying system path directly: {e}")
                    driver = uc.Chrome(
                        options=options,
                        driver_executable_path=system_driver_path,
                        use_subprocess=True,
                    )
                    self._apply_stealth(driver)
                    return driver
            else:
                driver = uc.Chrome(options=options, use_subprocess=True)
                self._apply_stealth(driver)
                return driver
        except Exception as e:
            print(f"Failed to initialize Chrome: {e}")
            raise

    def _apply_stealth(self, driver):
        """Apply JS stealth patches to hide automation signals."""
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": STEALTH_JS
            })
        except Exception as e:
            print(f"⚠️ Could not apply stealth JS (non-fatal): {e}")

    def _random_sleep(self, min_sec=2, max_sec=6):
        """Sleep for a random duration to mimic human behavior."""
        duration = random.uniform(min_sec, max_sec)
        time.sleep(duration)

    def get_top_reviews(self, product_url, count=2, driver=None):
        """Get the top reviews for a product."""
        driver_created = False
        if not driver:
            driver = self._get_driver()
            driver_created = True

        if not product_url.startswith("http"):
            if driver_created:
                driver.quit()
            return "No reviews found"

        original_window = None
        if not driver_created:
            original_window = driver.current_window_handle
            driver.switch_to.new_window("tab")

        reviews = []
        try:
            driver.get(product_url)
            self._random_sleep(3, 7)  # Anti-detection: randomized delay

            # Close any popups
            try:
                close_buttons = driver.find_elements(
                    By.XPATH, "//button[contains(@aria-label, 'Close')]"
                )
                for btn in close_buttons[:2]:
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except Exception:
                        pass
            except Exception:
                pass

            # Scroll down to load reviews (with human-like random pauses)
            for _ in range(5):
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                except Exception:
                    ActionChains(driver).send_keys(Keys.END).perform()
                self._random_sleep(0.8, 2.0)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # FIX: Amazon uses <li data-hook="review">, NOT <div>
            # Use tag-agnostic search to be resilient to future changes
            review_containers = soup.find_all(attrs={"data-hook": "review"})

            seen = set()
            for review_el in review_containers:
                try:
                    review_body_span = review_el.find(
                        "span", {"data-hook": "review-body"}
                    )
                    if review_body_span:
                        # FIX: get text directly from the review-body span
                        # Inner spans may include "Read more" text, so prefer
                        # the first meaningful inner span or fall back to direct text
                        inner_spans = review_body_span.find_all("span")
                        if inner_spans:
                            # Filter out "Read more" type spans
                            review_text = ""
                            for span in inner_spans:
                                span_text = span.get_text(strip=True)
                                if span_text.lower() not in ("read more", "read less"):
                                    review_text += span_text + " "
                            review_text = review_text.strip()
                        else:
                            review_text = review_body_span.get_text(strip=True)

                        if (
                            review_text
                            and review_text not in seen
                            and len(review_text) > 20
                        ):
                            reviews.append(review_text[:500])
                            seen.add(review_text)
                            if len(reviews) >= count:
                                break
                except Exception:
                    continue

        except Exception as e:
            print(f"Error scraping reviews from {product_url}: {e}")
            self.save_screenshot(driver, "error_reviews")

        finally:
            if driver_created:
                driver.quit()
            elif original_window:
                try:
                    driver.close()
                    driver.switch_to.window(original_window)
                except Exception:
                    pass

        return " || ".join(reviews) if reviews else "No reviews found"

    def scrape_amazon_products(
        self, query, max_products=5, review_count=2, status_callback=None
    ):
        """Scrape Amazon products based on a search query."""
        driver = self._get_driver()

        try:
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"

            if status_callback:
                status_callback(f"🔍 Searching for '{query}'...", None)

            driver.get(search_url)
            self._random_sleep(3, 7)  # Anti-detection: randomized delay

            # Close popups
            try:
                close_buttons = driver.find_elements(
                    By.XPATH, "//button[contains(@aria-label, 'Close')]"
                )
                for btn in close_buttons[:2]:
                    try:
                        btn.click()
                    except Exception:
                        pass
            except Exception:
                pass

            # Also dismiss any location/delivery popups
            try:
                dismiss_buttons = driver.find_elements(
                    By.XPATH, "//input[@data-action-type='DISMISS']"
                )
                for btn in dismiss_buttons[:2]:
                    try:
                        btn.click()
                    except Exception:
                        pass
            except Exception:
                pass

            self._random_sleep(2, 5)  # Anti-detection: randomized delay

            products = []
            items = driver.find_elements(
                By.CSS_SELECTOR, "div[data-component-type='s-search-result']"
            )

            if len(items) == 0:
                items = driver.find_elements(
                    By.CSS_SELECTOR, "div.s-result-item[data-component-type]"
                )

            # Filter out items without an ASIN (ads/placeholders)
            valid_items = []
            for item in items:
                asin = item.get_attribute("data-asin")
                if asin and asin.strip():
                    valid_items.append(item)

            items = valid_items[:max_products]

            if status_callback:
                status_callback(f"✅ Found {len(items)} items. Processing...", None)

            if len(items) == 0:
                print("No items found.")
                screenshot_path = self.save_screenshot(driver, "no_items_found")
                if status_callback and screenshot_path:
                    status_callback("⚠️ No items found!", screenshot_path)
                return products

            for i, item in enumerate(items):
                if status_callback:
                    status_callback(
                        f"⚙️ Processing item {i + 1}/{len(items)}...", None
                    )

                try:
                    # Scroll to item
                    ActionChains(driver).move_to_element(item).perform()
                    self._random_sleep(0.3, 1.0)

                    # --- Extract ASIN directly from data attribute ---
                    product_id = item.get_attribute("data-asin") or "N/A"

                    # --- Extract title ---
                    # FIX: structure is <a> > <h2> > <span>, so use "h2 span"
                    title = "N/A"
                    title_selectors = [
                        "h2 span",
                        "span.a-size-base-plus",
                        "span.a-size-medium",
                    ]
                    for selector in title_selectors:
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, selector)
                            if title_elem and title_elem.text.strip():
                                title = title_elem.text.strip()
                                break
                        except Exception:
                            continue

                    # --- Extract price ---
                    price = "N/A"
                    try:
                        price_whole = item.find_element(
                            By.CSS_SELECTOR, "span.a-price-whole"
                        )
                        price_frac = item.find_element(
                            By.CSS_SELECTOR, "span.a-price-fraction"
                        )
                        if price_whole and price_frac:
                            price = f"${price_whole.text.strip()}{price_frac.text.strip()}"
                    except Exception:
                        try:
                            price_elem = item.find_element(
                                By.CSS_SELECTOR, "span.a-price span.a-offscreen"
                            )
                            if price_elem:
                                price = price_elem.get_attribute("textContent").strip()
                        except Exception:
                            pass

                    # --- Extract rating ---
                    # FIX: use aria-label on the rating link/element
                    rating = "N/A"
                    try:
                        rating_elem = item.find_element(
                            By.CSS_SELECTOR, "[aria-label*='out of 5 stars']"
                        )
                        rating_label = rating_elem.get_attribute("aria-label")
                        # e.g. "4.3 out of 5 stars, rating details"
                        match = re.search(r"([\\d.]+)\\s+out of", rating_label)
                        if match:
                            rating = match.group(1)
                    except Exception:
                        pass

                    # --- Extract review count ---
                    # FIX: review count is in <a aria-label="X ratings">
                    total_reviews = "N/A"
                    try:
                        reviews_elem = item.find_element(
                            By.CSS_SELECTOR, "a[aria-label*='ratings']"
                        )
                        # Text is like "(821)" or "821"
                        reviews_text = reviews_elem.text.strip().strip("()")
                        if reviews_text:
                            total_reviews = reviews_text
                    except Exception:
                        # Fallback: try span near star ratings
                        try:
                            reviews_elem = item.find_element(
                                By.CSS_SELECTOR,
                                "span[aria-label*='ratings']",
                            )
                            total_reviews = reviews_elem.get_attribute(
                                "aria-label"
                            ).split()[0]
                        except Exception:
                            pass

                    # --- Extract product link ---
                    # FIX: use a[href*='/dp/'] instead of "h2 a"
                    product_link = "N/A"
                    try:
                        link_elem = item.find_element(
                            By.CSS_SELECTOR, "a[href*='/dp/']"
                        )
                        href = link_elem.get_attribute("href")
                        if href:
                            # FIX: was hardcoded to amazon.in
                            product_link = (
                                href
                                if href.startswith("http")
                                else "https://www.amazon.com" + href
                            )
                            # Extract ASIN from URL as fallback
                            if product_id == "N/A":
                                match = re.search(r"/dp/([A-Z0-9]+)", href)
                                if match:
                                    product_id = match.group(1)
                    except Exception:
                        pass

                    # Skip if we couldn't extract minimum info
                    if product_id == "N/A" and product_link == "N/A":
                        print(
                            f"Skipping item {i} - could not extract product info"
                        )
                        continue

                except Exception as e:
                    print(f"Error processing item {i}: {str(e)[:100]}")
                    continue

                # Get reviews
                if status_callback:
                    status_callback(
                        f"📝 Scraping reviews for product {i + 1}...", None
                    )

                top_reviews = self.get_top_reviews(
                    product_link, count=review_count, driver=None
                )

                products.append(
                    [product_id, title, rating, total_reviews, price, top_reviews]
                )
                print(f"✓ Added product: {product_id} - {title[:40]}...")

                # --- Anti-detection: cool-down every 3 products ---
                if (i + 1) % 3 == 0 and (i + 1) < len(items):
                    cool_down = random.uniform(15, 30)
                    if status_callback:
                        status_callback(f"⏳ Cooling down for {cool_down:.0f}s to avoid detection...", None)
                    print(f"⏳ Cooling down for {cool_down:.0f}s...")
                    time.sleep(cool_down)

                # --- Anti-detection: restart browser every 5 products ---
                if (i + 1) % 5 == 0 and (i + 1) < len(items):
                    print("🔄 Restarting browser to reset fingerprint...")
                    if status_callback:
                        status_callback("🔄 Restarting browser session...", None)
                    driver.quit()
                    self._random_sleep(5, 12)
                    driver = self._get_driver()
                    driver.get(search_url)
                    self._random_sleep(3, 6)
                    # Re-find items after browser restart
                    items = driver.find_elements(
                        By.CSS_SELECTOR, "div[data-component-type='s-search-result']"
                    )
                    valid_items = []
                    for it in items:
                        asin = it.get_attribute("data-asin")
                        if asin and asin.strip():
                            valid_items.append(it)
                    items = valid_items[:max_products]

        except Exception as e:
            print(f"Fatal error in scrape_amazon_products: {e}")
            if status_callback:
                status_callback(f"❌ Fatal error: {str(e)[:100]}", None)

        finally:
            driver.quit()

        return products

    def save_to_csv(self, data, filename="amazon_product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "product_id",
                    "product_title",
                    "rating",
                    "total_reviews",
                    "price",
                    "top_reviews",
                ]
            )
            writer.writerows(data)

        print(f"✅ Data saved to {path}")


# Example usage
if __name__ == "__main__":  # FIX: was "name"
    scraper = AmazonScraper()

    def status_callback(message, screenshot_path=None):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    products = scraper.scrape_amazon_products(
        query="laptop",
        max_products=5,
        review_count=2,
        status_callback=status_callback,
    )

    scraper.save_to_csv(products)

    print(f"\\n\\n{'=' * 80}")
    print(f"Successfully scraped {len(products)} products")
    print(f"{'=' * 80}\\n")

    for product in products:
        print(
            f"📦 {product[0]} | {product[1][:50]}... | ⭐ {product[2]} | Reviews: {product[3]}"
        )