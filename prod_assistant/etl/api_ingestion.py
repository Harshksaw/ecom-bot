import os
from typing import List, Literal
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore

from prod_assistant.utils.model_loader import ModelLoader
from prod_assistant.utils.config_loader import load_config
from prod_assistant.etl.api_fetcher import AmazonFetcher, BestBuyFetcher


class APIIngestionPipeline:
    """
    Check AstraDB for existing results; if insufficient, fetch from
    Amazon or Best Buy via RapidAPI and store the new documents.
    """

    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.fetcher_config = self.config["api_fetcher"]
        self.top_k = self.config["retriever"]["top_k"]
        self.min_threshold = self.fetcher_config["min_results_threshold"]

        model_loader = ModelLoader()
        collection_name = self.config["astra_db"]["collection_name"]

        self.vstore = AstraDBVectorStore(
            embedding=model_loader.load_embeddings(),
            collection_name=collection_name,
            api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
            token=os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        )

    def check_existing(self, query: str) -> List[Document]:
        return self.vstore.similarity_search(query, k=self.top_k)

    def has_sufficient_results(self, docs: List[Document]) -> bool:
        return len(docs) >= self.min_threshold

    def ingest(self, query: str, source: str) -> List[Document]:
        print(f"[APIIngestionPipeline] Fetching from {source}...")
        if source == "bestbuy":
            fetcher = BestBuyFetcher()
        else:
            fetcher = AmazonFetcher()

        docs = fetcher.fetch(query)
        if docs:
            inserted = self.vstore.add_documents(docs)
            print(f"[APIIngestionPipeline] Inserted {len(inserted)} documents into AstraDB.")
        else:
            print("[APIIngestionPipeline] No documents returned from API.")
        return docs

    def check_and_fetch(
        self, query: str, source: str = "amazon"
    ) -> Literal["already_exists", "fetched_and_stored"]:
        existing = self.check_existing(query)
        if self.has_sufficient_results(existing):
            print(f"[APIIngestionPipeline] AstraDB already has {len(existing)} results. Skipping API fetch.")
            return "already_exists"

        self.ingest(query, source)
        return "fetched_and_stored"
