import os
import asyncio
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_mcp_adapters import MCPAdapter
from langchain_astradb import AstraDBVectorStore

from prod_assistant.utils.model_loader import ModelLoader
from prod_assistant.utils.config_loader import load_config

class AgenticRAG:
    """Agentic RAG pipeline using LangChain ReAct Agent + RapidAPI MCP."""

    def __init__(self):
        load_dotenv()
        self.config = load_config()
        
        self.model_loader = ModelLoader()
        self.llm = self.model_loader.load_llm()
        self.checkpointer = MemorySaver()

        # Initialize AstraDB for local cache checks
        collection_name = self.config["astra_db"]["collection_name"]
        
        # Load embeddings early
        self.embeddings = self.model_loader.load_embeddings()

        # Use None initially so we don't crash before it's used
        self.vstore = AstraDBVectorStore(
            embedding=self.embeddings,
            collection_name=collection_name,
            api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
            token=os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        )
        
        # Agent app
        self.app = None
        
    async def async_init(self):
        """Load MCP tools asynchronously and build the agent."""
        
        # 1. Local Cache Tool (AstraDB)
        @tool
        def astradb_search(query: str) -> str:
            """Check cached products first from the AstraDB vector store."""
            try:
                results = self.vstore.similarity_search(query, k=self.config.get("retriever", {}).get("top_k", 5))
                if not results:
                    return "No cached products found."
                return "\n\n".join([doc.page_content + f" (Metadata: {doc.metadata})" for doc in results])
            except Exception as e:
                return f"Error searching cache: {e}"

        # 2. Connect to RapidAPI MCP
        rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.rapidapi_adapter = MCPAdapter(
            server_url="https://mcp.rapidapi.com",
            transport_type="streamable_http",
            headers={"X-RapidAPI-Key": rapidapi_key}
        )
        
        try:
            await self.rapidapi_adapter.connect()
            mcp_tools = await self.rapidapi_adapter.get_tools()
            print("✅ RapidAPI MCP tools loaded successfully.")
        except Exception as e:
            print(f"Warning: Failed to load MCP tools — {e}")
            mcp_tools = []

        # 3. Combine tools and build the React Agent
        self.tools = [astradb_search] + mcp_tools
        self.app = create_react_agent(self.llm, self.tools, checkpointer=self.checkpointer)

    async def run(self, query: str, thread_id: str = "default_thread", **kwargs) -> str:
        """Run the workflow for a given query and return the final answer."""
        if not self.app:
            await self.async_init()
            
        result = await self.app.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        return result["messages"][-1].content

# ---------- Standalone Test ----------
if __name__ == "__main__":
    async def main():
        rag_agent = AgenticRAG()
        answer = await rag_agent.run("What is the price of iPhone 16?")
        print("\nFinal Answer:\n", answer)
        
    asyncio.run(main())
