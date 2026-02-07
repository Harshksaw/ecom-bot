import os
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document
from typing import List
from  prod_assistant.utils.config_loader import load_config
from  prod_assistant.utils.model_loader import ModelLoader
from dotenv import load_dotenv



class Retiever:
    def __init__(self):
        
        self.model_loader=ModelLoader()
        self.config = load_config()
        self._load_env_variables()
        self.vstore = None
        self.retiever = None

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


    def load_retiever(self):
        """
        Load the retriever
        """
        if not self.vstore:
            collection_name = self.config["astra_db"]["collection_name"]
            self.vstore = AstraDBVectorStore(
                api_endpoint=self.db_api_endpoint,
                collection_name=collection_name,
                application_token=self.db_application_token,
                keyspace=self.db_keyspace,
            )


        if not self.retriever:
            top_k = self.config["retriever"]["top_k"] if "retriever" in self.config else 3
            retriever = self.vstore.as_retriever(search_kwargs={"k": top_k})

        return retriever

    def call_retriever(self):
        retriever = self.load_retiever()
        output = retriever.invoke()
        return output



if __name__ == "__main__":
    retirever_obj = Retiever()
    user_query = "Can you suggest a good budget laptop?"
    results = retiriever_obj.call_retriever(user_query)

    for idx, doc in enumerate(results,1):
        print(f"{idx + 1}. {doc.page_content}")
    print(results)
