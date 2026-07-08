from dotenv import load_dotenv

from research_agent.agent import ToolCallLoggingCallbackHandler, build_agent_executor


def main() -> None:
    load_dotenv()

    print("Initializing Research Agent...")
    # Change this to whichever local model you have installed that supports tool calling
    agent_executor = build_agent_executor(model_name="gemini-2.5-flash")
    log_handler = ToolCallLoggingCallbackHandler()

    questions = [
        "Read the file data/sample.txt and tell me what company we are researching.",
        "Now, search the web to find out the latest news about that company."
        " Keep it brief.",
        "What was the name of the company again?"
        " I'm checking if you remember our earlier conversation.",
        "Also, please read data/sample.pdf and briefly summarize what it is about.",
        "Based on that PDF, who coined the term 'machine learning' and when?",
        "According to the PDF, what are the foundations of machine learning?",
    ]

    config = {"configurable": {"thread_id": "session_1"}, "callbacks": [log_handler]}

    for q in questions:
        print(f"\n--- Question ---\n{q}\n")
        try:
            response = agent_executor.invoke({"messages": [("user", q)]}, config=config)
            content = response["messages"][-1].content
            if isinstance(content, list):
                content = content[0].get("text", str(content))
            print(f"\n--- Answer ---\n{content}\n")
        except Exception as e:
            print(f"\n--- Error ---\nAn error occurred: {e}")
            print(
                "Make sure you have set the GEMINI_API_KEY correctly in your .env file."
            )
            break


if __name__ == "__main__":
    main()
