import os
import sys
import json
from dotenv import load_dotenv
from prod_assistant.utils.config_loader import load_config
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from prod_assistant.logger import GLOBAL_LOGGER as log
from prod_assistant.exception.custom_exception import ProductAssistantException
import asyncio


class ApiKeyManager:
    def __init__(self):
        self.api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
            "ASTRA_DB_API_ENDPOINT": os.getenv("ASTRA_DB_API_ENDPOINT"),
            "ASTRA_DB_APPLICATION_TOKEN": os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            "ASTRA_DB_KEYSPACE": os.getenv("ASTRA_DB_KEYSPACE"),
        }

        # Just log loaded keys (don't print actual values)
        for key, val in self.api_keys.items():
            if val:
                log.info(f"{key} loaded from environment")
            else:
                log.warning(f"{key} is missing from environment")

    def get(self, key: str):
        return self.api_keys.get(key)

class ModelLoader:
    """
    Loads embedding models and LLMs based on config and environment.
    """

    def __init__(self):
        self.api_key_mgr = ApiKeyManager()
        self.config = load_config()
        log.info("YAML config loaded", config_keys=list(self.config.keys()))

    

    def load_embeddings(self):
        """
        Load and return embedding model from Google Generative AI.
        """
        try:
            model_name = self.config["embedding_model"]["model_name"]
            log.info("Loading embedding model", model=model_name)

            # Patch: Ensure an event loop exists for gRPC aio
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY")  # type: ignore
            )
        except Exception as e:
            log.error("Error loading embedding model", error=str(e))
            raise ProductAssistantException("Failed to load embedding model", sys)


    def _build_llm(self, provider_key: str):
        """
        Instantiate a single LLM from config. Returns None if API key is missing.
        """
        llm_block = self.config["llm"]
        if provider_key not in llm_block:
            return None

        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_output_tokens", 2048)

        if provider == "google":
            api_key = self.api_key_mgr.get("GOOGLE_API_KEY")
            if not api_key:
                log.warning("Skipping Google LLM — GOOGLE_API_KEY missing")
                return None
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=max_tokens
            )

        elif provider == "groq":
            api_key = self.api_key_mgr.get("GROQ_API_KEY")
            if not api_key:
                log.warning("Skipping Groq LLM — GROQ_API_KEY missing")
                return None
            return ChatGroq(
                model=model_name,
                api_key=api_key,  # type: ignore
                temperature=temperature,
            )

        elif provider == "openai":
            api_key = self.api_key_mgr.get("OPENAI_API_KEY")
            if not api_key:
                log.warning("Skipping OpenAI LLM — OPENAI_API_KEY missing")
                return None
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature
            )

        else:
            log.warning("Unsupported LLM provider, skipping", provider=provider)
            return None

    def load_llm(self):
        """
        Load the primary LLM (from LLM_PROVIDER env var) with automatic
        fallback to all other configured providers in config order.
        """
        llm_block = self.config["llm"]
        primary_key = os.getenv("LLM_PROVIDER", "openai")

        # Build primary first
        primary = self._build_llm(primary_key)
        if primary is None:
            log.error("Primary LLM could not be loaded", provider=primary_key)
            raise ValueError(f"Primary LLM provider '{primary_key}' failed to load — check API key and config")

        log.info("Primary LLM loaded", provider=primary_key)

        # Build fallbacks from remaining providers in config order
        fallbacks = []
        for key in llm_block:
            if key == primary_key:
                continue
            llm = self._build_llm(key)
            if llm is not None:
                fallbacks.append(llm)
                log.info("Fallback LLM registered", provider=key)

        if not fallbacks:
            log.warning("No fallback LLMs available — running with primary only")
            return primary

        log.info("LLM chain ready", primary=primary_key, fallbacks=[k for k in llm_block if k != primary_key])
        return primary.with_fallbacks(fallbacks)


if __name__ == "__main__":
    loader = ModelLoader()

    # Test Embedding
    embeddings = loader.load_embeddings()
    print(f"Embedding Model Loaded: {embeddings}")
    result = embeddings.embed_query("Hello, how are you?")
    print(f"Embedding Result: {result}")

    # Test LLM
    llm = loader.load_llm()
    print(f"LLM Loaded: {llm}")
    result = llm.invoke("Hello, how are you?")
    print(f"LLM Result: {result.content}")