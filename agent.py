"""
NazarSetu Autonomous Agent Engine.

Coordinates multi-step tool execution, maintains genuine action trails,
and drives conversational complaint tracking.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from config import OPENAI_API_KEY, OPENAI_MODEL
from tools import (
    OPENAI_TOOLS,
    execute_tool_call,
    find_responsible_ward,
    select_department,
    check_duplicate,
    register_complaint,
    get_complaint_status,
    get_complaint_timeline,
)
from vision import is_openai_configured


class ActionTrail:
    """Records genuine execution steps taken by the agent."""

    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def record_step(
        self,
        tool_name: str,
        title: str,
        explanation: str,
        input_args: Dict[str, Any],
        output_result: Any,
        status: str = "success"
    ) -> Dict[str, Any]:
        step = {
            "step_number": len(self.steps) + 1,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "tool_name": tool_name,
            "title": title,
            "explanation": explanation,
            "input_args": input_args,
            "output_result": output_result,
            "status": status,
        }
        self.steps.append(step)
        return step

    def get_steps(self) -> List[Dict[str, Any]]:
        return list(self.steps)

    def clear(self):
        self.steps.clear()


def run_reporting_agent_pipeline(
    issue_type: str,
    city: str,
    locality: str,
    image_hash: str,
    landmark: Optional[str] = None
) -> Tuple[Dict[str, Any], ActionTrail]:
    """
    Autonomous pipeline for citizen complaint processing before registration:
    1. select_department(issue_type)
    2. find_responsible_ward(city, locality)
    3. check_duplicate(issue_type, locality, image_hash)
    
    Generates a true execution trail from real Python function outputs.
    """
    trail = ActionTrail()
    pipeline_state: Dict[str, Any] = {
        "issue_type": issue_type,
        "city": city,
        "locality": locality,
        "landmark": landmark,
        "image_hash": image_hash,
    }

    # Step 1: Department Routing
    dept_res = select_department(issue_type=issue_type)
    dept_status = "success" if dept_res.get("is_supported") else "warning"
    trail.record_step(
        tool_name="select_department",
        title="Department Routing",
        explanation=f"Evaluated civic issue '{issue_type}' against municipal operational responsibilities.",
        input_args={"issue_type": issue_type},
        output_result=dept_res,
        status=dept_status,
    )
    pipeline_state["department"] = dept_res.get("department", "General Grievance Cell")

    # Step 2: Ward Assignment
    ward_res = find_responsible_ward(city=city, locality=locality)
    ward_status = "success" if ward_res.get("is_supported") else "warning"
    trail.record_step(
        tool_name="find_responsible_ward",
        title="Ward & Jurisdiction Lookup",
        explanation=f"Queried local ward dataset for '{locality}' within {city}.",
        input_args={"city": city, "locality": locality},
        output_result=ward_res,
        status=ward_status,
    )
    if ward_res.get("is_supported"):
        pipeline_state["ward"] = ward_res.get("ward")
        pipeline_state["ward_id"] = ward_res.get("ward_id")
        pipeline_state["nodal_officer"] = ward_res.get("nodal_officer")
    else:
        pipeline_state["ward"] = f"Unassigned ({locality})"
        pipeline_state["ward_id"] = "UNASSIGNED"

    # Step 3: Duplicate Guard Check
    dup_res = check_duplicate(
        issue_type=issue_type,
        locality=locality,
        image_hash=image_hash,
    )
    dup_status = "warning" if dup_res.get("is_duplicate") else "success"
    trail.record_step(
        tool_name="check_duplicate",
        title="Smart Duplicate Guard",
        explanation="Computed SHA-256 image signature and checked against unresolved database records.",
        input_args={"issue_type": issue_type, "locality": locality, "image_hash": image_hash[:16] + "..."},
        output_result=dup_res,
        status=dup_status,
    )
    pipeline_state["duplicate_check"] = dup_res

    return pipeline_state, trail


def run_registration_agent_action(
    confirmed_details: Dict[str, Any],
    trail: Optional[ActionTrail] = None
) -> Tuple[Dict[str, Any], ActionTrail]:
    """
    Executes complaint registration upon explicit citizen confirmation.
    Appends the real event to the ActionTrail.
    """
    if trail is None:
        trail = ActionTrail()

    reg_res = register_complaint(confirmed_details=confirmed_details)
    reg_status = "success" if reg_res.get("status") == "registered" else "error"

    trail.record_step(
        tool_name="register_complaint",
        title="Official Database Registration",
        explanation="Validated citizen confirmation and wrote persistent record to SQLite database.",
        input_args={"confirmed": confirmed_details.get("confirmed"), "issue_type": confirmed_details.get("issue_type")},
        output_result=reg_res,
        status=reg_status,
    )

    return reg_res, trail


def extract_tracking_id_from_text(text: str) -> Optional[str]:
    """Find pattern NS-DEMO-XXXXXXXX or CIV-DEMO-XXXX in user query."""
    match = re.search(r"\b(NS-DEMO-[A-Z0-9]{4,12}|CIV-DEMO-[A-Z0-9]{4,12})\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def run_tracking_chat_agent(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    trail: Optional[ActionTrail] = None
) -> Dict[str, Any]:
    """
    Autonomous tracking assistant that accepts user questions and retrieves real database data.
    Uses OpenAI function calling when available, or autonomous tool dispatcher in local mode.
    """
    if trail is None:
        trail = ActionTrail()

    # Check if OpenAI is configured for full model-driven tool calling
    if is_openai_configured():
        try:
            return _run_openai_tracking_loop(user_message, chat_history, trail)
        except Exception as e:
            # Graceful fallback to deterministic tool execution
            return _run_deterministic_tracking_agent(user_message, trail, fallback_note=f"AI Agent fallback: {e}")

    return _run_deterministic_tracking_agent(user_message, trail)


def _run_openai_tracking_loop(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]],
    trail: ActionTrail
) -> Dict[str, Any]:
    """Run genuine OpenAI tool-calling loop for tracking queries."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = (
        "You are NazarSetu Complaint Tracking Assistant, an autonomous municipal agent. "
        "Your duty is to answer citizens' questions about their civic complaints. "
        "Use your tools (get_complaint_status, get_complaint_timeline) to retrieve real stored records. "
        "Rules: "
        "1. Never invent or hallucinate complaint IDs or statuses. "
        "2. If a citizen does not provide a tracking ID (format NS-DEMO-XXXXXXXX), politely ask for it. "
        "3. When you receive tool outputs, summarize them clearly with current status (Pending / In Progress / Resolved), "
        "department, and last updated time. "
        "4. Be professional, empathetic, and direct."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for m in chat_history[-6:]:
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})

    # Step 1: Model decides if a tool is needed
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        tools=OPENAI_TOOLS,
        tool_choice="auto",
        temperature=0.1
    )
    choice = response.choices[0].message

    complaint_data = None
    timeline_data = None

    if choice.tool_calls:
        # Agent chose to call tools
        messages.append(choice)
        for tool_call in choice.tool_calls:
            t_name = tool_call.function.name
            t_args = json.loads(tool_call.function.arguments or "{}")
            
            # Execute genuine Python tool function
            tool_output = execute_tool_call(t_name, t_args)

            if t_name == "get_complaint_status" and tool_output.get("status") == "found":
                complaint_data = tool_output
            elif t_name == "get_complaint_timeline" and tool_output.get("status") == "success":
                timeline_data = tool_output.get("events")

            # Record in Action Trail
            trail.record_step(
                tool_name=t_name,
                title=f"Autonomous Tool: {t_name}",
                explanation=f"Agent invoked {t_name} with parameters: {t_args}",
                input_args=t_args,
                output_result=tool_output,
                status="success" if tool_output.get("status") in ["found", "success"] else "warning"
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": t_name,
                "content": json.dumps(tool_output)
            })

        # Second completion to formulate response based on actual tool outputs
        follow_up = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.1
        )
        assistant_reply = follow_up.choices[0].message.content
    else:
        assistant_reply = choice.content

    return {
        "reply": assistant_reply,
        "complaint_data": complaint_data,
        "timeline_data": timeline_data,
        "trail": trail,
        "mode": "openai_agent",
    }


def _run_deterministic_tracking_agent(
    user_message: str,
    trail: ActionTrail,
    fallback_note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministic tracking agent that parses queries, extracts IDs, and executes real tools.
    Used when running offline or in Fallback Mode.
    """
    extracted_id = extract_tracking_id_from_text(user_message)
    complaint_data = None
    timeline_data = None

    if not extracted_id:
        # Prompt citizen for complaint ID
        reply = (
            "I would be glad to check your complaint status! Please provide your **Tracking ID** "
            "(for example, `NS-DEMO-A101B202` or `NS-DEMO-XXXXXXXX`) so I can retrieve the official records from our municipal database."
        )
        return {
            "reply": reply,
            "complaint_data": None,
            "timeline_data": None,
            "trail": trail,
            "mode": "local_agent",
            "fallback_note": fallback_note,
        }

    # Step 1: Execute get_complaint_status
    status_res = get_complaint_status(complaint_id=extracted_id)
    s_status = "success" if status_res.get("status") == "found" else "warning"
    trail.record_step(
        tool_name="get_complaint_status",
        title="Retrieve Stored Complaint Status",
        explanation=f"Queried SQLite database for tracking ID '{extracted_id}'.",
        input_args={"complaint_id": extracted_id},
        output_result=status_res,
        status=s_status,
    )

    # Step 2: Execute get_complaint_timeline
    timeline_res = get_complaint_timeline(complaint_id=extracted_id)
    t_status = "success" if timeline_res.get("status") == "success" else "warning"
    trail.record_step(
        tool_name="get_complaint_timeline",
        title="Retrieve Chronological Event Timeline",
        explanation=f"Fetched event history for '{extracted_id}'.",
        input_args={"complaint_id": extracted_id},
        output_result=timeline_res,
        status=t_status,
    )

    if status_res.get("status") == "found":
        complaint_data = status_res
        timeline_data = timeline_res.get("events", [])
        curr_status = complaint_data["current_status"]
        dept = complaint_data["department"]
        issue = complaint_data["issue_type"]
        ward = complaint_data["ward"]
        locality = complaint_data["locality"]
        city = complaint_data["city"]
        updated = complaint_data["updated_at"]

        reply = (
            f"Here are the live municipal records for **{extracted_id}**:\n\n"
            f"- **Issue:** {issue}\n"
            f"- **Current Status:** **{curr_status.upper()}**\n"
            f"- **Department:** {dept}\n"
            f"- **Jurisdiction:** {ward} ({locality}, {city})\n"
            f"- **Last Updated:** {updated}\n\n"
            f"*Summary:* {complaint_data.get('description', 'No description recorded.')}"
        )
    else:
        reply = (
            f"I checked the municipal database, but could not find any active complaint with ID **{extracted_id}**. "
            f"Please verify the tracking number and try again."
        )

    return {
        "reply": reply,
        "complaint_data": complaint_data,
        "timeline_data": timeline_data,
        "trail": trail,
        "mode": "local_agent",
        "fallback_note": fallback_note,
    }
