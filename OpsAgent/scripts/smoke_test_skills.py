import sys
import os
import time
from dotenv import load_dotenv

# Ensure OpsAgent root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.skills.summarization_skill import summarize_text
from src.skills.task_extraction_skill import extract_tasks_and_reminders
from src.skills.date_extraction_skill import extract_dates_and_updates
from src.skills.event_extraction_skill import extract_event_details
from src.skills.review_skill import review_pr_diff
from src.skills.file_review_skill import review_file_content
from src.marshal.router import classify_intent


def run_skills_smoke_test():
    """
    Runs each skill and router function against short sample input using the real, unmocked Anthropic API.
    Prints pass/fail status and output for each skill.
    """
    print("=== OpsAgent Skills Live API Smoke Test Checklist ===")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[FAIL] ERROR: ANTHROPIC_API_KEY environment variable is not set!")
        sys.exit(1)

    tests = [
        (
            "summarize_text",
            lambda: summarize_text("Discussed project timeline. Deadline is Friday. Alex to finish design."),
        ),
        (
            "extract_tasks_and_reminders",
            lambda: extract_tasks_and_reminders("Remind me tomorrow to review PR #42 for Sarah"),
        ),
        (
            "extract_dates_and_updates",
            lambda: extract_dates_and_updates("Project kick-off is on 2026-09-01. Design approved."),
        ),
        (
            "extract_event_details",
            lambda: extract_event_details("Schedule a team sync tomorrow at 3pm with John and Alice"),
        ),
        (
            "review_pr_diff",
            lambda: review_pr_diff("diff --git a/main.py b/main.py\n+def run():\n+    print('Hello World')", title="Add run function"),
        ),
        (
            "review_file_content",
            lambda: review_file_content("def calculate(x: int) -> int:\n    return x * 2", file_path="calc.py"),
        ),
        (
            "classify_intent",
            lambda: classify_intent("Can you review PR #101 in owner/repo?"),
        ),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n--- Testing Skill: {name} ---")
        start_time = time.time()
        try:
            res = test_func()
            elapsed = time.time() - start_time
            print(f"[PASS] {name} ({elapsed:.2f}s)")
            print(f"Result Preview: {str(res)[:150]}...")
            passed += 1
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[FAIL] {name} ({elapsed:.2f}s)")
            print(f"Error ({type(e).__name__}): {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Smoke Test Summary: {passed} PASSED, {failed} FAILED out of {len(tests)} skills.")
    print("=" * 50)

    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run_skills_smoke_test()
