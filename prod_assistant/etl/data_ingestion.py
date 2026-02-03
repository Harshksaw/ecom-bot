import os
import pandas as pd
from dotenv import load_dotenv

from typing import List
from langchain_core.documents import documents
from langchain_astradb import AstraDBVectorStore

from prod_assistant.utils.config_loader import load_config
from prod_assistant.utils.model_loader import ModelLoader
from prod_assistant.logger import GLOBAL_LOGGER


class DataIngestion:
    def __init__(self):
        self.config = load_config()
        self.logger = GLOBAL_LOGGER
        self.vector_store = AstraDBVectorStore(
            collection_name=self.config["astra_db"]["collection_name"],
            embedding_function=self.config["astra_db"]["embedding_function"],
            astra_db_client=self.config["astra_db"]["astra_db_client"],
        )

    def _load_env_variables(self):
        pass


    def store_in_vector_db(self):
        pass

    def _get_csv_path(self):
        pass

    def load_csv(self):
        pass

    def transform_data(self):
        pass

    def run_pipelne(self):
        pass

  

