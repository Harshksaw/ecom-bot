import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin

class BooksToScrapeScraper:
    """Scraper for books.toscrape.com - a friendly educational scraping sandbox."""
    
    BASE_URL = "https://books.toscrape.com/"
    CATALOGUE_URL = BASE_URL + "catalogue/"

    RATING_MAP = {
        "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
    }

    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_soup(self, url):
        """Fetch a page and return a BeautifulSoup object."""
        headers = {"User-Agent": "BooksBot/1.0 (Educational Scraper)"}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return None

    def get_categories(self):
        """Scrape all category names and URLs from the sidebar."""
        soup = self.get_soup(self.BASE_URL)
        if not soup:
            return []
            
        sidebar = soup.select_one(".side_categories ul li ul")
        categories = []
        if sidebar:
            for li in sidebar.select("li"):
                a = li.find("a")
                if a:
                    name = a.text.strip()
                    href = a["href"]
                    # Fix relative URL
                    abs_url = urljoin(self.BASE_URL, href)
                    categories.append({"name": name, "url": abs_url})
        return categories

    def scrape_book_detail(self, book_url, category="Unknown"):
        """Scrape full details from a single book's detail page."""
        soup = self.get_soup(book_url)
        if not soup:
            return None
        
        try:
            # Title
            title = soup.select_one(".product_main h1").text.strip()
            
            # Price
            price = soup.select_one(".product_main .price_color").text.strip()
            
            # Availability
            avail_tag = soup.select_one(".product_main .availability")
            availability = avail_tag.text.strip() if avail_tag else "Unknown"
            stock_match = re.search(r"\((\d+) available\)", availability)
            stock_count = int(stock_match.group(1)) if stock_match else 0
            
            # Star Rating
            star_tag = soup.select_one(".product_main .star-rating")
            rating_class = star_tag["class"][1] if star_tag else "Zero"
            rating = self.RATING_MAP.get(rating_class, 0)
            
            # Description
            desc_tag = soup.select_one("#product_description ~ p")
            description = desc_tag.text.strip() if desc_tag else ""
            
            # Image URL
            img_tag = soup.select_one(".item.active img")
            image_url = ""
            if img_tag:
                image_url = urljoin(book_url, img_tag["src"])
            
            # Product Information table
            product_info = {}
            table = soup.select_one("table.table-striped")
            if table:
                for row in table.select("tr"):
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        product_info[th.text.strip()] = td.text.strip()
            
            return {
                "title": title,
                "price": price,
                "price_numeric": float(price.replace("£", "").replace("Â", "").strip()) if "£" in price else 0.0,
                "rating": rating,
                "rating_label": rating_class,
                "availability": availability,
                "stock_count": stock_count,
                "category": category,
                "description": description,
                "image_url": image_url,
                "detail_url": book_url,
                "upc": product_info.get("UPC", ""),
                "product_type": product_info.get("Product Type", ""),
                "price_excl_tax": product_info.get("Price (excl. tax)", ""),
                "price_incl_tax": product_info.get("Price (incl. tax)", ""),
                "tax": product_info.get("Tax", ""),
                "num_reviews": int(product_info.get("Number of reviews", "0")),
            }
        except Exception as e:
            print(f"Error parsing book {book_url}: {e}")
            return None

    def scrape_category_books(self, category_url, max_books=None):
        """Scrape book URLs from a category (handles pagination)."""
        book_urls = []
        current_url = category_url
        
        while current_url:
            soup = self.get_soup(current_url)
            if not soup:
                break
                
            articles = soup.select("article.product_pod")
            
            for article in articles:
                link = article.select_one("h3 a")
                if link:
                    href = link["href"]
                    abs_url = urljoin(current_url, href)
                    book_urls.append(abs_url)
            
            if max_books and len(book_urls) >= max_books:
                return book_urls[:max_books]

            # Check for next page
            next_btn = soup.select_one(".pager .next a")
            if next_btn:
                current_url = urljoin(current_url, next_btn["href"])
            else:
                current_url = None
        
        return book_urls

    def scrape_category(self, category_name, max_books=5, status_callback=None):
        """Scrape books from a specific category by name."""
        categories = self.get_categories()
        target_cat = next((c for c in categories if c["name"].lower() == category_name.lower()), None)
        
        if not target_cat:
            print(f"Category '{category_name}' not found.")
            return []

        if status_callback:
            status_callback(f"📂 Scraping category: {target_cat['name']}...", None)
            
        book_urls = self.scrape_category_books(target_cat["url"], max_books)
        
        if status_callback:
             status_callback(f"📚 Found {len(book_urls)} books. Fetching details...", None)

        books = []
        for i, url in enumerate(book_urls):
            if status_callback:
                status_callback(f"⚙️ Processing book {i+1}/{len(book_urls)}...", None)
                
            book = self.scrape_book_detail(url, category=target_cat["name"])
            if book:
                books.append(book)
                time.sleep(0.2)  # Polite delay

        return books

    def save_books(self, books, filename="books_data.json"):
        """Save scraped books to JSON file."""
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(books, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(books)} books to {path}")
        return path

    def save_to_csv(self, books, filename="product_reviews.csv"):
        """Save to CSV in the format expected by the UI/ingestion pipeline."""
        # Map book fields to the expected CSV columns:
        # product_id, product_title, rating, total_reviews, price, top_reviews
        
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "product_id", "product_title", "rating",
                "total_reviews", "price", "top_reviews",
            ])
            
            for book in books:
                # Construct a "review" from description since the site doesn't have real reviews
                review_text = book.get("description", "")
                if not review_text:
                    review_text = "No description available."
                    
                writer.writerow([
                    book.get("upc", "N/A"),
                    book.get("title", "N/A"),
                    f"{book.get('rating', 0)}/5",
                    "0",  # No real reviews on this site
                    book.get("price", "N/A"),
                    review_text
                ])
        print(f"✅ Data saved to {path}")


if __name__ == "__main__":
    scraper = BooksToScrapeScraper()
    print("Fetching categories...")
    cats = scraper.get_categories()
    print(f"Found {len(cats)} categories: {[c['name'] for c in cats[:5]]}...")
    
    # Scrape 'Travel' category as test
    books = scraper.scrape_category("Travel", max_books=3)
    scraper.save_books(books)