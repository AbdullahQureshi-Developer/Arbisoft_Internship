import sys
import os
from dotenv import load_dotenv

# Ensure OpsAgent root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.llm_client import call_claude


def run_api_smoke_test():
    """
    Live, unmocked smoke test for the Anthropic API.
    Makes a single live call using call_claude() with a trivial prompt.
    Fails loudly with the real API error if the call does not succeed.
    """
    print("=== OpsAgent Live API Smoke Test ===")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[FAIL] ERROR: ANTHROPIC_API_KEY environment variable is not set!")
        sys.exit(1)

    print(f"API Key detected: {api_key[:6]}...{api_key[-4:]}")
    print("Sending live test prompt to Anthropic API via call_claude()...")

    try:
        response = call_claude(
            prompt="Reply with the exact text 'OK' and nothing else.",
            system_prompt="You are a smoke test validation assistant.",
        )
        print(f"[PASS] Live API call succeeded!")
        print(f"Response Content: {response.strip()}")
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Live API call FAILED with error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Detail: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_api_smoke_test()
