import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
import shutil

class AmazonScraper:
    def __init__(self, output_dir="data"):
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

    def _get_driver(self):
        """Initialize and return a Chrome driver (local or remote)."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # selenium_url = os.getenv("SELENIUM_URL")
        # if selenium_url:
        #     print(f"Connecting to remote browser at {selenium_url}")
        #     return webdriver.Remote(command_executor=selenium_url, options=options)

        system_browser_path = None
        system_driver_path = None
        possible_browser_paths = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
        possible_driver_paths = [
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            "/usr/bin/chromedriver",
            "/usr/bin/chromium-driver"
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
                # Copy driver to a writable location since uc needs to patch it
                writable_driver_path = os.path.join(os.getcwd(), "chromedriver_copy")
                try:
                    shutil.copy2(system_driver_path, writable_driver_path)
                    os.chmod(writable_driver_path, 0o755)
                    print(f"Copied driver to: {writable_driver_path}")
                    return uc.Chrome(options=options, driver_executable_path=writable_driver_path, use_subprocess=True)
                except Exception as e:
                    print(f"Failed to copy/patch driver, trying system path directly: {e}")
                    return uc.Chrome(options=options, driver_executable_path=system_driver_path, use_subprocess=True)
            else:
                return uc.Chrome(options=options, use_subprocess=True)
        except Exception as e:
            print(f"Failed to initialize Chrome: {e}")
            raise

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
            driver.switch_to.new_window('tab')

        reviews = []
        try:
            driver.get(product_url)
            time.sleep(4)

            # Close any popups
            try:
                close_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Close')]")
                for btn in close_buttons[:2]:  # Limit to first 2
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass

            # Scroll down to load reviews
            for _ in range(5):
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                except:
                    ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find reviews - Amazon uses div[data-hook="review"]
            review_containers = soup.find_all("div", {"data-hook": "review"})
            
            seen = set()
            for review_div in review_containers:
                try:
                    # Find the review body span
                    review_body_span = review_div.find("span", {"data-hook": "review-body"})
                    if review_body_span:
                        # Get the actual text from spans inside
                        review_text = ""
                        for span in review_body_span.find_all("span"):
                            review_text += span.get_text(strip=True) + " "
                        review_text = review_text.strip()
                        
                        if review_text and review_text not in seen and len(review_text) > 20:
                            reviews.append(review_text[:500])  # Limit to 500 chars
                            seen.add(review_text)
                            if len(reviews) >= count:
                                break
                except Exception as e:
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
                except:
                    pass

        return " || ".join(reviews) if reviews else "No reviews found"

    def scrape_amazon_products(self, query, max_products=5, review_count=2, status_callback=None):
        """Scrape Amazon products based on a search query."""
        driver = self._get_driver()
        try:
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
            
            if status_callback:
                status_callback(f"🔍 Searching for '{query}'...", None)
            
            driver.get(search_url)
            time.sleep(3)

            # Close popups
            try:
                close_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Close')]")
                for btn in close_buttons[:2]:
                    try:
                        btn.click()
                    except:
                        pass
            except:
                pass

            time.sleep(2)
            products = []

            # Get search result items
            items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
            
            if len(items) == 0:
                items = driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-component-type]")

            # Limit to max_products
            items = items[:max_products]

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
                    status_callback(f"⚙️ Processing item {i+1}/{len(items)}...", None)

                try:
                    # Scroll to item
                    ActionChains(driver).move_to_element(item).perform()
                    time.sleep(0.3)

                    # Extract title - try multiple selectors
                    title = "N/A"
                    title_selectors = ["h2 a span", "h2 span", "span.a-size-base-plus", "span.a-size-medium"]
                    for selector in title_selectors:
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, selector)
                            if title_elem:
                                title = title_elem.text.strip()
                                if title:
                                    break
                        except:
                            continue

                    # Extract price
                    price = "N/A"
                    price_selectors = ["span.a-price-whole", "span.a-price"]
                    for selector in price_selectors:
                        try:
                            price_elem = item.find_element(By.CSS_SELECTOR, selector)
                            if price_elem:
                                price = price_elem.text.strip()
                                if price:
                                    break
                        except:
                            continue

                    # Extract rating
                    rating = "N/A"
                    try:
                        rating_elem = item.find_element(By.CSS_SELECTOR, "span.a-icon-star-small span")
                        rating_text = rating_elem.text.strip()
                        rating = rating_text.split()[0] if rating_text else "N/A"
                    except:
                        pass

                    # Extract review count
                    total_reviews = "N/A"
                    try:
                        reviews_elem = item.find_element(By.CSS_SELECTOR, "span[aria-label*='based on']")
                        reviews_text = reviews_elem.text.strip()
                        match = re.search(r"(\\d+(?:,\\d+)?)\\s+", reviews_text)
                        if match:
                            total_reviews = match.group(1)
                    except:
                        pass

                    # Extract product link and ASIN
                    product_id = "N/A"
                    product_link = "N/A"
                    
                    # Try to find link with href containing /dp/
                    link_elem = None
                    link_selectors = ["h2 a", "a[href*='/dp/']", "a[href*='/p/']"]
                    
                    for selector in link_selectors:
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, selector)
                            if link_elem:
                                break
                        except:
                            continue

                    if link_elem:
                        href = link_elem.get_attribute("href")
                        if href:
                            product_link = href if href.startswith("http") else "https://www.amazon.in" + href
                            
                            # Extract ASIN
                            match = re.search(r"/dp/([A-Z0-9]+)", href)
                            if match:
                                product_id = match.group(1)

                    # Skip if we couldn't extract minimum info
                    if product_id == "N/A" or product_link == "N/A":
                        print(f"Skipping item {i} - could not extract product info")
                        continue

                except Exception as e:
                    print(f"Error processing item {i}: {str(e)[:100]}")
                    continue

                # Get reviews
                if status_callback:
                    status_callback(f"📝 Scraping reviews for product {i+1}...", None)

                top_reviews = self.get_top_reviews(product_link, count=review_count, driver=None)
                
                products.append([product_id, title, rating, total_reviews, price, top_reviews])
                print(f"✓ Added product: {product_id} - {title[:40]}...")

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
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)
        
        print(f"✅ Data saved to {path}")


# Example usage
if __name__ == "__main__":
    scraper = AmazonScraper()
    
    def status_callback(message, screenshot_path=None):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    products = scraper.scrape_amazon_products(
        query="laptop",
        max_products=5,
        review_count=2,
        status_callback=status_callback
    )
    
    scraper.save_to_csv(products)
    
    print(f"\\n\\n{'='*80}")
    print(f"Successfully scraped {len(products)} products")
    print(f"{'='*80}\\n")
    
    for product in products:
        print(f"📦 {product[0]} | {product[1][:50]}... | ⭐ {product[2]} | Reviews: {product[3]}")