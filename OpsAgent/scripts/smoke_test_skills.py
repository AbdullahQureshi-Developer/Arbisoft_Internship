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

    long_sample_document = (
        "# Q3 Engineering Operations & Sprint Sync Meeting Notes\n\n"
        "## 1. Architecture & Migration Updates\n"
        "- Decided to migrate legacy authentication service to OAuth2.0 / OIDC.\n"
        "- PostgreSQL database upgrade from v14 to v16 completed successfully on staging environment.\n"
        "- Switched CI/CD runners from GitHub-hosted to self-hosted ARM64 instances for a 40% cost reduction.\n\n"
        "## 2. Key Deadlines & Scheduled Events\n"
        "- Project kick-off meeting is scheduled for 2026-09-01T10:00:00.\n"
        "- Staging deployment freeze will begin on 2026-09-15T18:00:00.\n"
        "- Final production release candidate audit is due on 2026-10-01T12:00:00.\n"
        "- Customer demo sync with executive leadership on 2026-10-15T15:30:00.\n\n"
        "## 3. Action Items & Assignees\n"
        "- Alice needs to refactor the payment gateway integration and add full integration tests by next Friday.\n"
        "- Bob must review PR #402 for security vulnerabilities and approve before merge.\n"
        "- Charlie is assigned to update the API documentation and publish the OpenAPI spec to the Developer Portal.\n"
        "- David will configure Datadog dashboards and set up PagerDuty alerts for API latency spikes.\n"
        "- Eve to schedule a Follow-up Architecture Review meeting next week with Principal Engineers.\n"
        "- Frank needs to verify backup recovery procedures and document the RTO/RPO metrics.\n"
    )

    tests = [
        (
            "summarize_text (Short Input)",
            lambda: summarize_text("Discussed project timeline. Deadline is Friday. Alex to finish design."),
        ),
        (
            "extract_tasks_and_reminders (Short Input)",
            lambda: extract_tasks_and_reminders("Remind me tomorrow to review PR #42 for Sarah"),
        ),
        (
            "extract_dates_and_updates (Short Input)",
            lambda: extract_dates_and_updates("Project kick-off is on 2026-09-01. Design approved."),
        ),
        (
            "extract_tasks_and_reminders (Long Multi-Section Document)",
            lambda: extract_tasks_and_reminders(long_sample_document),
        ),
        (
            "extract_dates_and_updates (Long Multi-Section Document)",
            lambda: extract_dates_and_updates(long_sample_document),
        ),
        (
            "summarize_text (Long Multi-Section Document)",
            lambda: summarize_text(long_sample_document),
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
