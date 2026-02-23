import os
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document
from typing import List
from  prod_assistant.utils.config_loader import load_config
from  prod_assistant.utils.model_loader import ModelLoader
from dotenv import load_dotenv

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter

class Retriever:
    def __init__(self):
        self._load_env_variables()
        self.model_loader=ModelLoader()
        self.config = load_config()
        self.vstore = None
        self.retriever = None

    def _load_env_variables(self):
        load_dotenv()
        
        required_vars = ["GOOGLE_API_KEY", "ASTRA_DB_API_ENDPOINT", "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE"]
        
        missing_vars = [var for var in required_vars if os.getenv(var) is None]
        if missing_vars:
            raise EnvironmentError(f"Missing environment variables: {missing_vars}")
        
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.db_api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")


    def load_retriever(self):
        """
        Load the retriever
        """
        if not self.vstore:
            collection_name = self.config["astra_db"]["collection_name"]
            embedding = self.model_loader.load_embeddings()
            self.vstore = AstraDBVectorStore(
                api_endpoint=self.db_api_endpoint,
                collection_name=collection_name,
                token=self.db_application_token,
                namespace=self.db_keyspace,
                embedding=embedding,
            )


        if not self.retriever:
            top_k = self.config["retriever"]["top_k"] if "retriever" in self.config else 3
            mmr_retriever = self.vstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": top_k, "fetch_k": 20,
                "lambda_mult": 0.7,
                "score_threshold": 0.3
                })
            print("MMR Retriever loaded")

            llm = self.model_loader.load_llm()
            print("LLM loaded")

            compressor = LLMChainFilter.from_llm(llm)
            print("Compressor loaded")

            self.retriever = ContextualCompressionRetriever(
                base_retriever=mmr_retriever,
                base_compressor=compressor
            )

            return self.retriever


        return self.retriever

    def call_retriever(self, query):
        retriever = self.load_retriever()
        output = retriever.invoke(query)
        return output



if __name__ == "__main__":
    retriever_obj = Retriever()
    user_query = "Can you suggest a good budget laptop?"
    retrieved_obj =  Retriever()
    retrieved_docs = retriever_obj.call_retriever(user_query)


    def _format_docs(docs: List[Document]) -> str:

        if not docs:
            return "No relevant documents found"

            formatted_chunks = []
            for d in docs:
                meta = d.metadata or {}
                formatted = {
                    f"Title: {meta.get('title', 'N/A')}",
                    f"Category: {meta.get('category', 'N/A')}",
                    f"Price: {meta.get('price', 'N/A')}",
                    f"Description: {meta.get('description', 'N/A')}",
                    f"Content: {d.page_content.strinp()}"
                }
                formatted_chunks.append(formatted)
            return "\n\n---\n\n".join(formatted_chunks)
                 

        retrieved_contexts = [_format_docs(doc) for doc in retrieved_docs]
        context_score = evaluate_context_precision(query, response,retrieved_contexts)
        relevancy_score = evaluate_response_relevancy(query , response , retrieved_contexts)

        print(f"Context Precision: {context_score}")
        print(f"Response Relevancy: {relevancy_score}")
        return retrieved_contexts