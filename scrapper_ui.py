import streamlit as st
import asyncio
from prod_assistant.workflow.agentic_workflow_with_mcp_websearch import AgenticRAG

st.set_page_config(page_title="E-Com AI Assistant", page_icon="🛍️")

st.title("🛍️ E-Com AI Assistant")
st.info("ℹ️ Powered by LangGraph ReAct agent and RapidAPI's MCP Server. I dynamically check local AstraDB cache or fetch live data!")

# Initialize the RAG Agent in session state
if "rag_agent" not in st.session_state:
    st.session_state.rag_agent = AgenticRAG()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What product are you looking for?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Agent is reasoning..."):
            try:
                # Async run
                response = asyncio.run(st.session_state.rag_agent.run(prompt))
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error("❌ I encountered an error executing the agent!")
                st.exception(e)