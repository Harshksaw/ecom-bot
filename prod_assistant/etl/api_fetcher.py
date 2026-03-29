import os
import requests
from typing import List
from langchain_core.documents import Document
from prod_assistant.utils.config_loader import load_config


class AmazonFetcher:
    """Fetches products and reviews from Amazon via RapidAPI."""

    def __init__(self):
        self.config = load_config()["api_fetcher"]
        self.amazon_cfg = self.config["amazon"]
        self.max_products = self.config["max_products"]
        self.max_reviews = self.config["max_reviews_per_product"]
        self.api_key = os.getenv("RAPIDAPI_KEY", "")
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.amazon_cfg["host"],
        }

    def _search_products(self, query: str) -> List[dict]:
        params = {
            "query": query,
            "page": "1",
            "country": self.amazon_cfg["country"],
            "sort_by": "RELEVANCE",
        }
        resp = requests.get(
            self.amazon_cfg["search_url"],
            headers=self.headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("data") or {}).get("products", [])[: self.max_products]

    def _fetch_reviews(self, asin: str) -> List[str]:
        params = {
            "asin": asin,
            "country": self.amazon_cfg["country"],
            "sort_by": "TOP_REVIEWS",
            "page": "1",
        }
        try:
            resp = requests.get(
                self.amazon_cfg["reviews_url"],
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            reviews = (data.get("data") or {}).get("reviews", [])[: self.max_reviews]
            return [
                f"{r.get('review_title', '')}: {r.get('review_comment', '')}"
                for r in reviews
            ]
        except Exception:
            return []

    def fetch(self, query: str) -> List[Document]:
        products = self._search_products(query)
        documents = []
        for p in products:
            asin = p.get("asin", "")
            reviews = self._fetch_reviews(asin)
            doc = Document(
                page_content=" | ".join(reviews) if reviews else "No reviews available.",
                metadata={
                    "product_id": asin,
                    "product_title": p.get("product_title", ""),
                    "price": p.get("product_price", ""),
                    "rating": p.get("product_star_rating", ""),
                    "total_reviews": p.get("product_num_ratings", ""),
                    "source": "amazon",
                },
            )
            documents.append(doc)
        return documents


class BestBuyFetcher:
    """Fetches products and reviews from Best Buy via RapidAPI."""

    def __init__(self):
        self.config = load_config()["api_fetcher"]
        self.bb_cfg = self.config["bestbuy"]
        self.max_products = self.config["max_products"]
        self.max_reviews = self.config["max_reviews_per_product"]
        self.api_key = os.getenv("RAPIDAPI_KEY", "")
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.bb_cfg["host"],
        }

    def _search_products(self, query: str) -> List[dict]:
        params = {
            "keyword": query,
            "page": "1",
            "sortBy": "RELEVANCE",
        }
        resp = requests.get(
            self.bb_cfg["search_url"],
            headers=self.headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("searchProductList") or [])[: self.max_products]

    def _fetch_reviews(self, sku: str) -> List[str]:
        params = {
            "sku": sku,
            "page": "1",
            "sortBy": "TOP_RATED",
        }
        try:
            resp = requests.get(
                self.bb_cfg["reviews_url"],
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            reviews = (data.get("reviews") or [])[: self.max_reviews]
            return [
                f"{r.get('title', '')}: {r.get('comment', '')}"
                for r in reviews
            ]
        except Exception:
            return []

    def fetch(self, query: str) -> List[Document]:
        products = self._search_products(query)
        documents = []
        for p in products:
            sku = str(p.get("sku", ""))
            reviews = self._fetch_reviews(sku)
            doc = Document(
                page_content=" | ".join(reviews) if reviews else "No reviews available.",
                metadata={
                    "product_id": sku,
                    "product_title": p.get("name", ""),
                    "price": p.get("regularPrice", ""),
                    "rating": p.get("rating", ""),
                    "total_reviews": p.get("reviewCount", ""),
                    "source": "bestbuy",
                },
            )
            documents.append(doc)
        return documents
