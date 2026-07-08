import os
import sys
import uuid

import streamlit as st
from dotenv import load_dotenv

from research_agent.agent import ToolCallLoggingCallbackHandler, build_agent_executor


def build_ui() -> None:
    st.set_page_config(page_title="Research Agent App", page_icon="🕵️‍♂️")
    st.title("🕵️‍♂️ Research Agent")

    # Initialize session state for memory tracking and thread_id
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent_executor" not in st.session_state:
        load_dotenv()
        try:
            # We initialize it once per session
            st.session_state.agent_executor = build_agent_executor(
                model_name="gemini-2.5-flash"
            )
            st.session_state.log_handler = ToolCallLoggingCallbackHandler()
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            return

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if query := st.chat_input("Ask a question..."):
        # Append and display user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Agent execution
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                config = {
                    "configurable": {"thread_id": st.session_state.thread_id},
                    "callbacks": [st.session_state.log_handler],
                }

                try:
                    response = st.session_state.agent_executor.invoke(
                        {"messages": [("user", query)]}, config=config
                    )

                    # LangGraph returns a list of state messages, we grab the last one
                    content = response["messages"][-1].content
                    # Sometimes Gemini returns a list for content
                    if isinstance(content, list):
                        content = content[0].get("text", str(content))

                    st.markdown(content)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": content}
                    )

                except Exception as e:
                    st.error(f"Error calling model: {e}")
                    st.error("Make sure GEMINI_API_KEY is in your .env file and valid.")


def main() -> None:
    # This allows `agent-ui` to work as an entrypoint
    app_path = os.path.abspath(__file__)
    import subprocess

    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


if __name__ == "__main__":
    build_ui()
