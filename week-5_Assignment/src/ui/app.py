import streamlit as st
import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.agent.graph import build_graph
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

load_dotenv()

st.title("MCP LangGraph Agent Chat")

# Fail fast with a clear message instead of a confusing downstream error
# if the API key isn't configured.
if not os.getenv("ANTHROPIC_API_KEY"):
    st.error(
        "⚠️ ANTHROPIC_API_KEY is not set. Add it to your .env file or "
        "environment before starting a chat."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

_ERROR_PREFIX = "__AGENT_ERROR__:"


def _unwrap_exception(err: BaseException) -> BaseException:
    """Recursively unwrap nested ExceptionGroups (raised by asyncio/anyio
    TaskGroups, which stdio_client uses under the hood) to find the actual
    root-cause exception instead of a generic 'unhandled errors in a
    TaskGroup' message."""
    seen = getattr(err, "exceptions", None)
    while seen:
        err = seen[0]
        seen = getattr(err, "exceptions", None)
    return err


async def run_agent(query):
    server_script_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "mcp_server", "server.py"
    )
    server_params = StdioServerParameters(command="python", args=[server_script_path])

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                graph = build_graph(session)

                # Format history for LangChain
                lc_messages = []
                # Send the last 4 messages to retain memory context without using too many tokens
                recent_history = st.session_state.messages[-4:]
                for m in recent_history:
                    if m["role"] == "user":
                        lc_messages.append(HumanMessage(content=m["content"]))
                    else:
                        lc_messages.append(AIMessage(content=m["content"]))

                lc_messages.append(HumanMessage(content=query))
                initial_state = {"messages": lc_messages, "next_node": ""}

                final_response = ""
                async for event in graph.astream(
                    initial_state, {"recursion_limit": 20}
                ):
                    for node, state in event.items():
                        if "messages" in state:
                            last_message = state["messages"][-1]
                            if (
                                type(last_message).__name__ == "AIMessage"
                                and last_message.content
                                and not last_message.tool_calls
                            ):
                                final_response = last_message.content

                return final_response
    except Exception as graph_err:
        # Catch here — BEFORE the stdio_client __aexit__ wraps it in ExceptionGroup.
        # TaskGroups can nest ExceptionGroups multiple levels deep, so unwrap
        # recursively rather than grabbing exceptions[0] once.
        actual_err = _unwrap_exception(graph_err)
        actual_err_str = f"{type(actual_err).__name__}: {actual_err}"
        return f"{_ERROR_PREFIX}{actual_err_str}"


if prompt := st.chat_input("What would you like to ask?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking..."):
            try:
                response = asyncio.run(run_agent(prompt))
                # Handle cases where Claude returns a list of dictionaries for content
                if isinstance(response, list):
                    parsed_response = []
                    for item in response:
                        if isinstance(item, dict) and "text" in item:
                            parsed_response.append(item["text"])
                        else:
                            parsed_response.append(str(item))
                    response = "\n".join(parsed_response)
            except Exception as e:
                response = f"{_ERROR_PREFIX}{e}"

            # Interpret error strings
            if isinstance(response, str) and response.startswith(_ERROR_PREFIX):
                err_detail = response[len(_ERROR_PREFIX) :]
                if (
                    "429" in err_detail
                    or "RESOURCE_EXHAUSTED" in err_detail
                    or "rate_limit_error" in err_detail.lower()
                ):
                    response = "⚠️ **Rate limit hit.** You've exceeded the Claude API quota. Please wait a few minutes and try again."
                else:
                    response = f"❌ An error occurred: {err_detail}"
            elif not response:
                response = "❌ No response was returned by the agent."

            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
