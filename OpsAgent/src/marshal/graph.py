import time
import logging
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from src.hooks.logging_hook import log_call
from src.marshal.router import classify_intent, WorkflowIntent
from src.agents.github_agent import fetch_pr_diff, post_review_comment, FetchPRRequest, PostCommentRequest
from src.skills.review_skill import review_pr_diff
from src.skills.summarization_skill import summarize_text
from src.skills.task_extraction_skill import extract_tasks_and_reminders
from src.agents.todo_agent import save_extracted_tasks
from src.agents.reminder_agent import schedule_new_reminder, ScheduleReminderRequest

logger = logging.getLogger(__name__)


class OpsAgentState(TypedDict):
    message_text: str
    channel_id: str
    user_id: str
    thread_ts: Optional[str]
    intent: Optional[WorkflowIntent]
    result_text: str
    error: Optional[str]


@log_call
def classify_step(state: OpsAgentState) -> OpsAgentState:
    intent = classify_intent(state["message_text"])
    state["intent"] = intent
    return state


@log_call
def github_review_step(state: OpsAgentState) -> OpsAgentState:
    intent = state.get("intent")
    if not intent or not intent.pr_number:
        state["result_text"] = "⚠️ Could not identify PR number from your request."
        return state

    repo = intent.repo or "owner/repo"
    pr_num = intent.pr_number

    # Retry logic (1 retry with backoff)
    diff_res = None
    last_err = None
    for attempt in range(2):
        try:
            diff_res = fetch_pr_diff(FetchPRRequest(repo=repo, pr_number=pr_num))
            break
        except Exception as e:
            last_err = e
            time.sleep(1)

    if not diff_res:
        err_msg = f"❌ Failed to fetch PR #{pr_num} from GitHub ({repo}): {last_err}"
        logger.error(err_msg)
        state["result_text"] = err_msg
        state["error"] = str(last_err)
        return state

    try:
        # Run Review Skill
        review = review_pr_diff(diff_text=diff_res.diff, title=diff_res.title)

        # Post comment to GitHub
        post_res = post_review_comment(PostCommentRequest(repo=repo, pr_number=pr_num, body=review.comment_text))

        state["result_text"] = (
            f"✅ **GitHub Review Posted** for PR #{pr_num} ({repo})\n\n"
            f"**Summary**: {review.summary}\n\n"
            f"**Issues Identified**: {len(review.issues)}\n"
            f"🔗 [View Comment on GitHub]({post_res.html_url or diff_res.html_url})"
        )
    except Exception as e:
        state["result_text"] = f"⚠️ Analyzed PR #{pr_num}, but failed to post review comment: {e}"
        state["error"] = str(e)

    return state


@log_call
def task_reminder_step(state: OpsAgentState) -> OpsAgentState:
    text = state.get("intent").notes_text or state["message_text"] if state.get("intent") else state["message_text"]

    try:
        # 1. Summarize
        summary_res = summarize_text(text)

        # 2. Extract Tasks
        extraction_res = extract_tasks_and_reminders(text)

        # 3. Save Tasks
        save_res = save_extracted_tasks(extraction_res.tasks)

        # 4. Schedule Reminders
        scheduled_reminders = []
        for task in extraction_res.tasks:
            if task.reminder_delay_seconds:
                rem_res = schedule_new_reminder(
                    ScheduleReminderRequest(
                        channel_id=state["channel_id"],
                        user_id=state["user_id"],
                        message=task.description,
                        delay_seconds=task.reminder_delay_seconds,
                        task_id=save_res.saved_tasks[0].task_id if save_res.saved_tasks else None,
                    )
                )
                scheduled_reminders.append(rem_res)

        tasks_formatted = "\n".join([f"• {t.description} (Assignee: {t.assignee or 'Unassigned'})" for t in save_res.saved_tasks]) or "None"
        reminders_formatted = f"{len(scheduled_reminders)} reminder(s) scheduled." if scheduled_reminders else "No explicit reminder time requested."

        state["result_text"] = (
            f"📝 **Summary & Task Extraction Complete**\n\n"
            f"**Summary**:\n{summary_res.summary}\n\n"
            f"**Extracted Tasks ({len(save_res.saved_tasks)})**:\n{tasks_formatted}\n\n"
            f"⏰ **Reminders**: {reminders_formatted}"
        )
    except Exception as e:
        logger.error(f"Error in task & reminder step: {e}")
        state["result_text"] = f"❌ Error processing notes/tasks: {e}"
        state["error"] = str(e)

    return state


@log_call
def unknown_step(state: OpsAgentState) -> OpsAgentState:
    state["result_text"] = (
        "🤖 **OpsAgent Assistant**\n"
        "I can help you with:\n"
        "1. **GitHub PR Reviews**: Say `review PR #123` or `can you check PR 123`.\n"
        "2. **Tasks & Reminders**: Paste meeting notes and say `summarize these, extract tasks, and remind me tomorrow to follow up`."
    )
    return state


def route_decision(state: OpsAgentState) -> str:
    intent = state.get("intent")
    if not intent:
        return "unknown"
    if intent.intent_type == "github_review":
        return "github_review"
    elif intent.intent_type == "task_and_reminder":
        return "task_and_reminder"
    return "unknown"


# Build LangGraph Workflow
builder = StateGraph(OpsAgentState)
builder.add_node("classify", classify_step)
builder.add_node("github_review", github_review_step)
builder.add_node("task_and_reminder", task_reminder_step)
builder.add_node("unknown", unknown_step)

builder.set_entry_point("classify")
builder.add_conditional_edges(
    "classify",
    route_decision,
    {
        "github_review": "github_review",
        "task_and_reminder": "task_and_reminder",
        "unknown": "unknown",
    },
)
builder.add_edge("github_review", END)
builder.add_edge("task_and_reminder", END)
builder.add_edge("unknown", END)

ops_graph = builder.compile()


@log_call
def process_slack_message(message_text: str, channel_id: str, user_id: str, thread_ts: Optional[str] = None) -> str:
    """
    Unified entrypoint executing the OpsAgent LangGraph workflow.
    """
    initial_state: OpsAgentState = {
        "message_text": message_text,
        "channel_id": channel_id,
        "user_id": user_id,
        "thread_ts": thread_ts,
        "intent": None,
        "result_text": "",
        "error": None,
    }
    
    final_state = ops_graph.invoke(initial_state)
    return final_state["result_text"]
