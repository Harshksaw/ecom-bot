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
        status_placeholder = st.empty()
        with status_placeholder.status("Agent is working...", expanded=True) as status:
            try:
                # We need an async wrapper to run the stream generator
                async def process_stream():
                    full_response = ""
                    async for event in st.session_state.rag_agent.run_stream(prompt):
                        kind = event["event"]
                        
                        if kind == "on_chat_model_stream":
                            content = event["data"]["chunk"].content
                            if getattr(event["data"]["chunk"], "tool_calls", None):
                                # Skip streaming if it's formulating a tool call instead of text
                                pass
                            elif isinstance(content, str):
                                full_response += content
                                
                        elif kind == "on_tool_start":
                            tool_name = event["name"]
                            if tool_name == "search_amazon":
                                status.update(label=f"🔍 Searching Amazon live for '{event['data'].get('input', {}).get('query', '')}'...", state="running")
                                status.write(f"Calling tool `{tool_name}`...")
                            elif tool_name == "get_product_reviews":
                                status.update(label=f"📖 Reading live reviews for ASIN {event['data'].get('input', {}).get('asin', '')}...", state="running")
                                status.write(f"Calling tool `{tool_name}`...")
                            elif tool_name == "astradb_search":
                                status.update(label=f"🗄️ Checking local cache...", state="running")
                                status.write(f"Calling tool `{tool_name}`...")
                                
                        elif kind == "on_tool_end":
                            tool_name = event["name"]
                            status.write(f"✅ Finished tool: {tool_name}")
                            
                    status.update(label="Done processing!", state="complete")
                    return full_response

                final_text = asyncio.run(process_stream())
                st.markdown(final_text)
                st.session_state.messages.append({"role": "assistant", "content": final_text})
                
            except Exception as e:
                status.update(label="Error!", state="error")
                st.error("❌ I encountered an error executing the agent!")
                st.exception(e)