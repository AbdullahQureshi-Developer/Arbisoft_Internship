import time
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import TypedDict, Optional, List, Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from src.hooks.logging_hook import log_call
from src.marshal.router import classify_intent, WorkflowIntent
from src.agents.github_agent import (
    fetch_pr_diff,
    post_review_comment,
    FetchPRRequest,
    PostCommentRequest,
)
from src.skills.review_skill import review_pr_diff
from src.skills.summarization_skill import summarize_text
from src.skills.task_extraction_skill import extract_tasks_and_reminders
from src.skills.date_extraction_skill import extract_dates_and_updates
from src.skills.document_parser import parse_document
from src.agents.todo_agent import save_extracted_tasks, SaveTasksRequest
from src.agents.reminder_agent import schedule_new_reminder, ScheduleReminderRequest
from src.skills.event_extraction_skill import extract_event_details
from src.agents.calendar_agent import schedule_calendar_event, CreateEventRequest

load_dotenv()

logger = logging.getLogger(__name__)


class OpsAgentState(TypedDict):
    message_text: str
    channel_id: str
    user_id: str
    thread_ts: Optional[str]
    file_bytes: Optional[bytes]
    file_name: Optional[str]
    intent: Optional[WorkflowIntent]
    result_text: str
    error: Optional[str]


def _format_task_list(tasks: List[Any]) -> str:
    """Formats a list of extracted/saved tasks into bullet points."""
    return (
        "\n".join(
            [
                f"• {getattr(t, 'description', str(t))} (Assignee: {getattr(t, 'assignee', 'Unassigned') or 'Unassigned'})"
                for t in tasks
            ]
        )
        or "None"
    )


def _resolve_working_text(state: OpsAgentState) -> str:
    """Extracts working text from state intent notes_text or message_text, retrieving channel history if query is short."""
    intent = state.get("intent")
    if intent and intent.notes_text:
        return intent.notes_text

    msg_text = state.get("message_text", "")
    msg_lower = msg_text.lower()

    # If the user message is a short follow-up query referencing previous notes/tasks
    if len(msg_text.strip().split()) < 15 and any(
        kw in msg_lower
        for kw in ["action item", "meeting notes", "summarize", "task", "notes"]
    ):
        try:
            from src.memory.store import get_channel_history

            channel_id = state.get("channel_id", "")
            user_id = state.get("user_id", "")
            if channel_id and user_id:
                history = get_channel_history(
                    channel_id=channel_id, user_id=user_id, limit=5
                )
                past_msgs = [
                    h.message
                    for h in history
                    if h.message != msg_text and len(h.message) > 20
                ]
                if past_msgs:
                    return (
                        f"{msg_text}\n\nContext from Previous Channel Messages:\n"
                        + "\n---\n".join(past_msgs)
                    )
        except Exception as e:
            logger.warning(f"Could not retrieve channel history context: {e}")

    return msg_text


@log_call
def classify_step(state: OpsAgentState) -> OpsAgentState:
    if state.get("file_bytes") and state.get("file_name"):
        state["intent"] = None
        return state
    intent = classify_intent(state["message_text"])
    state["intent"] = intent
    return state


@log_call
def github_review_step(state: OpsAgentState) -> OpsAgentState:
    intent = state.get("intent")
    if not intent or not intent.pr_number:
        state["result_text"] = "⚠️ Could not identify PR number from your request."
        return state

    if not intent.repo:
        state["result_text"] = (
            "⚠️ Please specify the GitHub repository in 'owner/repo' format."
        )
        return state

    repo = intent.repo
    pr_num = intent.pr_number
    msg_lower = state["message_text"].lower()

    # Check if user explicitly asked to post/comment on GitHub
    should_post = any(k in msg_lower for k in ["post", "comment", "publish", "attach"])

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
        logger.exception(err_msg)
        state["result_text"] = err_msg
        state["error"] = str(last_err)
        return state

    try:
        # Run Review Skill
        review = review_pr_diff(diff_text=diff_res.diff, title=diff_res.title)
        issues_formatted = (
            "\n".join([f"• {issue}" for issue in review.issues]) or "None"
        )

        if should_post:
            # Post comment directly to GitHub
            post_res = post_review_comment(
                PostCommentRequest(
                    repo=repo, pr_number=pr_num, body=review.comment_text
                )
            )

            state["result_text"] = (
                f"I've published your review comment directly to GitHub PR #{pr_num}! 🚀\n\n"
                f"✅ **GitHub Review Posted** for PR #{pr_num} ({repo})\n\n"
                f"**Summary**: {review.summary}\n\n"
                f"**Issues Identified** ({len(review.issues)}):\n{issues_formatted}\n\n"
                f"🔗 [View Comment on GitHub]({post_res.html_url or diff_res.html_url})"
            )
        else:
            # Display review in Slack first and offer to post
            state["result_text"] = (
                f"I've completed the code review for PR #{pr_num}! Here is the breakdown: 🔍\n\n"
                f"🔍 **GitHub PR Review Complete** for PR #{pr_num} ({repo})\n\n"
                f"**Summary**:\n{review.summary}\n\n"
                f"**Issues Identified** ({len(review.issues)}):\n{issues_formatted}\n\n"
                f"**Detailed Review Comment**:\n{review.comment_text}\n\n"
                f"💡 **Post to GitHub Offer**: Would you like to post this review as an official comment on PR #{pr_num}? "
                f"Reply with `post to PR #{pr_num}`."
            )
    except Exception as e:
        state["result_text"] = f"⚠️ Analyzed PR #{pr_num}, but encountered an error: {e}"
        state["error"] = str(e)

    return state


@log_call
def task_reminder_step(state: OpsAgentState) -> OpsAgentState:
    text = _resolve_working_text(state)

    try:
        # 1. Summarize
        summary_res = summarize_text(text)

        # 2. Extract Tasks
        extraction_res = extract_tasks_and_reminders(text)

        # 3. Save Tasks scoped to user_id
        save_res = save_extracted_tasks(
            SaveTasksRequest(tasks=extraction_res.tasks, user_id=state["user_id"])
        )

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
                        task_id=save_res.saved_tasks[0].task_id
                        if save_res.saved_tasks
                        else None,
                    )
                )
                scheduled_reminders.append(rem_res)

        tasks_formatted = _format_task_list(save_res.saved_tasks)
        reminders_formatted = (
            f"{len(scheduled_reminders)} reminder(s) scheduled."
            if scheduled_reminders
            else "No explicit reminder time requested."
        )

        if not save_res.saved_tasks and not scheduled_reminders:
            from src.memory.store import get_tasks

            existing_tasks = get_tasks(user_id=state["user_id"])
            if existing_tasks:
                existing_formatted = _format_task_list(existing_tasks)
                state["result_text"] = (
                    f"Here are your saved action items from your meeting notes memory: 📋\n\n"
                    f"📋 **Saved Action Items ({len(existing_tasks)})**:\n{existing_formatted}"
                )
            else:
                state["result_text"] = (
                    f"I reviewed the query, but didn't find any new actionable tasks or reminders to schedule. 📝\n\n"
                    f"**Summary**:\n{summary_res.summary}\n\n"
                    f"**Extracted Tasks (0)**:\nNone\n\n"
                    f"⏰ **Reminders**: {reminders_formatted}"
                )
        else:
            state["result_text"] = (
                f"Got it! I've summarized your notes, saved the extracted tasks, and set up your reminders. 📝\n\n"
                f"📝 **Summary & Task Extraction Complete**\n\n"
                f"**Summary**:\n{summary_res.summary}\n\n"
                f"**Extracted Tasks ({len(save_res.saved_tasks)})**:\n{tasks_formatted}\n\n"
                f"⏰ **Reminders**: {reminders_formatted}"
            )
    except Exception as e:
        logger.exception(f"Error in task & reminder step: {e}")
        state["result_text"] = f"❌ Error processing notes/tasks: {e}"
        state["error"] = str(e)

    return state


@log_call
def calendar_schedule_step(state: OpsAgentState) -> OpsAgentState:
    text = _resolve_working_text(state)

    try:
        # 1. Extract event details via Skill
        extracted_event = extract_event_details(text)

        # 2. Call Calendar Agent (creates event via MCP tool)
        start_iso = extracted_event.start_time.isoformat()
        end_iso = extracted_event.end_time.isoformat()

        event_res = schedule_calendar_event(
            CreateEventRequest(
                title=extracted_event.title,
                start_time=start_iso,
                end_time=end_iso,
                attendees=extracted_event.attendees,
                user_id=state["user_id"],
            )
        )

        if (
            event_res.status == "auth_required"
            or getattr(event_res, "note", None) == "auth_required"
        ):
            from src.integrations.google.auth import generate_auth_token

            auth_token = generate_auth_token(state["user_id"])
            auth_url = f"http://localhost:8000/auth/google?token={auth_token}"
            state["result_text"] = (
                f"🔒 **Google Calendar Authentication Required**\n\n"
                f"You haven't connected your Google Calendar account yet!\n\n"
                f"👉 [Click Here to Connect Google Calendar]({auth_url})\n\n"
                f"Once connected, ask me again and I'll schedule **{extracted_event.title}** on your calendar! 📅"
            )
            return state

        attendees_str = (
            ", ".join(event_res.attendees) if event_res.attendees else "None"
        )

        state["result_text"] = (
            f"Sure thing! I've scheduled your event on Google Calendar. 📅\n\n"
            f"📅 **Calendar Event Scheduled**\n\n"
            f"**Title**: {event_res.title}\n"
            f"**Start Time**: {event_res.start_time}\n"
            f"**End Time**: {event_res.end_time}\n"
            f"**Attendees**: {attendees_str}\n\n"
            f"🔗 [View Calendar Event]({event_res.html_url})"
        )
    except Exception as e:
        logger.exception(f"Error in calendar schedule step: {e}")
        state["result_text"] = f"❌ Error scheduling calendar event: {e}"
        state["error"] = str(e)

    return state


@log_call
def document_processing_step(state: OpsAgentState) -> OpsAgentState:
    file_bytes = state.get("file_bytes")
    file_name = state.get("file_name", "document.pdf")
    user_id = state["user_id"]
    channel_id = state["channel_id"]

    try:
        if file_bytes is not None:
            doc_text = parse_document(file_bytes=file_bytes, filename=file_name)
        else:
            doc_text = state["message_text"]

        from src.memory.store import record_channel_message

        record_channel_message(
            channel_id=channel_id,
            user_id=user_id,
            role="assistant",
            message=f"Document Content (`{file_name}`):\n{doc_text[:1000]}",
        )

        combined_text = (
            f"{state['message_text']}\n\nDocument Content:\n{doc_text}".strip()
        )

        now = datetime.utcnow()

        # Run extraction skills in parallel
        with ThreadPoolExecutor() as executor:
            future_summary = executor.submit(summarize_text, combined_text)
            future_tasks = executor.submit(extract_tasks_and_reminders, combined_text)
            future_dates = executor.submit(
                lambda: extract_dates_and_updates(combined_text, reference_now=now)
            )

            summary_res = future_summary.result()
            task_res = future_tasks.result()
            dates_and_updates = future_dates.result()

        save_res = save_extracted_tasks(
            SaveTasksRequest(tasks=task_res.tasks, user_id=user_id)
        )

        routed_dates_info = []
        for date_item in dates_and_updates.dates:
            dt = date_item.date
            desc = date_item.description

            dt_naive = (
                dt.astimezone(timezone.utc).replace(tzinfo=None)
                if dt.tzinfo is not None
                else dt
            )
            time_until = dt_naive - now
            total_seconds = time_until.total_seconds()

            if total_seconds < 0:
                routed_dates_info.append(
                    f"• ⚠️ **{desc}** ({dt.strftime('%Y-%m-%d %H:%M')}) — *already past — not scheduled*"
                )
            elif total_seconds <= 4 * 3600:
                delay_sec = max(5, int(total_seconds))
                schedule_new_reminder(
                    ScheduleReminderRequest(
                        channel_id=channel_id,
                        user_id=user_id,
                        message=f"{desc} ({file_name})",
                        delay_seconds=delay_sec,
                    )
                )
                routed_dates_info.append(
                    f"• ⏰ **{desc}** ({dt.strftime('%Y-%m-%d %H:%M')}) — *Internal Reminder Scheduled*"
                )
            else:
                start_iso = dt.isoformat()
                end_iso = (dt + timedelta(minutes=30)).isoformat()
                cal_res = schedule_calendar_event(
                    CreateEventRequest(
                        title=f"{desc} ({file_name})",
                        start_time=start_iso,
                        end_time=end_iso,
                        attendees=[],
                        user_id=user_id,
                    )
                )
                link_str = (
                    f" [View Calendar Event]({cal_res.html_url})"
                    if cal_res.html_url
                    else ""
                )
                routed_dates_info.append(
                    f"• 📅 **{desc}** ({dt.strftime('%Y-%m-%d %H:%M')}) — *Google Calendar Event Scheduled*{link_str}"
                )

        tasks_formatted = _format_task_list(save_res.saved_tasks)
        dates_formatted = "\n".join(routed_dates_info) or "No dates found."
        updates_formatted = (
            "\n".join([f"• {u}" for u in dates_and_updates.updates]) or "None"
        )

        state["result_text"] = (
            f"I've processed your uploaded document (`{file_name}`). Here is the summary and extracted items: 📄\n\n"
            f"📄 **Document Processing Complete** (`{file_name}`)\n\n"
            f"**Summary**:\n{summary_res.summary}\n\n"
            f"📋 **Extracted Tasks ({len(save_res.saved_tasks)})**:\n{tasks_formatted}\n\n"
            f"📅 **Extracted Dates & Scheduled Items**:\n{dates_formatted}\n\n"
            f"💡 **Notable Updates & Decisions**:\n{updates_formatted}"
        )
    except ValidationError as ve:
        raw_inputs = [err.get("input") for err in ve.errors()]
        logger.exception(
            f"Pydantic ValidationError processing document `{file_name}`: {ve}\n"
            f"Validation errors detail: {ve.errors()}\n"
            f"Raw/Failed input values: {raw_inputs}"
        )
        state["result_text"] = (
            f"❌ Error processing document `{file_name}`: Model output failed schema validation ({ve.error_count()} validation error(s): {ve})"
        )
        state["error"] = str(ve)
    except Exception as e:
        logger.exception(f"Error processing document `{file_name}`: {e}")
        state["result_text"] = f"❌ Error processing document `{file_name}`: {e}"
        state["error"] = str(e)

    return state


@log_call
def unknown_step(state: OpsAgentState) -> OpsAgentState:
    text = _resolve_working_text(state)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.llm_client import get_llm

        llm = get_llm()
        system_prompt = (
            "You are Marshal, a friendly and helpful AI assistant in Slack. "
            "Respond naturally, warmly, and concisely to user messages like greetings, thanks, acknowledgments, or general chat. "
            "Keep your response direct, friendly, and short (1-2 sentences). Do not use rigid bullet point lists unless specifically asked."
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text),
        ]
        response = llm.invoke(messages)
        res_content = response.content
        if isinstance(res_content, list):
            res_content = "".join(
                [
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in res_content
                ]
            )
        elif not isinstance(res_content, str):
            res_content = str(res_content)

        state["result_text"] = res_content
    except Exception as e:
        logger.exception(f"Error in unknown conversational step: {e}")
        state["result_text"] = (
            "You're very welcome! Let me know if you need any help with PR reviews, tasks, or calendar scheduling. 😊"
        )

    return state


def route_decision(state: OpsAgentState) -> str:
    if state.get("file_bytes") and state.get("file_name"):
        return "document_processing"
    intent = state.get("intent")
    if not intent:
        return "unknown"
    if intent.intent_type == "github_review":
        return "github_review"
    elif intent.intent_type == "task_and_reminder":
        return "task_and_reminder"
    elif intent.intent_type == "calendar_schedule":
        return "calendar_schedule"
    return "unknown"


# Build LangGraph Workflow
builder = StateGraph(OpsAgentState)
builder.add_node("classify", classify_step)
builder.add_node("github_review", github_review_step)
builder.add_node("task_and_reminder", task_reminder_step)
builder.add_node("calendar_schedule", calendar_schedule_step)
builder.add_node("document_processing", document_processing_step)
builder.add_node("unknown", unknown_step)

builder.set_entry_point("classify")
builder.add_conditional_edges(
    "classify",
    route_decision,
    {
        "github_review": "github_review",
        "task_and_reminder": "task_and_reminder",
        "calendar_schedule": "calendar_schedule",
        "document_processing": "document_processing",
        "unknown": "unknown",
    },
)
builder.add_edge("github_review", END)
builder.add_edge("task_and_reminder", END)
builder.add_edge("calendar_schedule", END)
builder.add_edge("document_processing", END)
builder.add_edge("unknown", END)

ops_graph = builder.compile()


@log_call
def process_slack_message(
    message_text: str,
    channel_id: str,
    user_id: str,
    thread_ts: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
) -> str:
    """
    Unified entrypoint executing the OpsAgent LangGraph workflow.
    """
    from src.memory.store import record_channel_message

    record_channel_message(
        channel_id=channel_id, user_id=user_id, role="user", message=message_text
    )

    initial_state: OpsAgentState = {
        "message_text": message_text,
        "channel_id": channel_id,
        "user_id": user_id,
        "thread_ts": thread_ts,
        "file_bytes": file_bytes,
        "file_name": file_name,
        "intent": None,
        "result_text": "",
        "error": None,
    }

    final_state = ops_graph.invoke(initial_state)

    if final_state.get("result_text"):
        record_channel_message(
            channel_id=channel_id,
            user_id=user_id,
            role="assistant",
            message=final_state["result_text"],
        )

    return final_state["result_text"]
