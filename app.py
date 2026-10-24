"""
NazarSetu — Agentic AI Civic Action Platform.

Main Streamlit Application combining:
- Citizen Reporting Studio with Issue DNA and Smart Duplicate Guard
- Autonomous Agent Action Trail
- Conversational Complaint Tracking Assistant
- Admin Command Center for municipal status updates
"""

import os
from pathlib import Path
from PIL import Image
import pandas as pd
import streamlit as st

from config import (
    SUPPORTED_CATEGORIES,
    VALID_STATUSES,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    DEMO_WARDS_CSV,
    DB_PATH,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
import database
import tools
import vision
import agent
import components

# Page Configuration
st.set_page_config(
    page_title="NazarSetu — AI Civic Action Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database and seed sample complaints if empty
database.seed_demo_complaints()

# Initialize session state variables
if "action_trail" not in st.session_state:
    st.session_state.action_trail = agent.ActionTrail()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "Namaste! I am the **NazarSetu Civic Assistant**. "
                "How may I help you today? You can ask me to track an existing complaint "
                "(e.g., `NS-DEMO-A101B202` or `Check my pothole complaint`), or ask about municipal departments."
            )
        }
    ]

if "last_registered_id" not in st.session_state:
    st.session_state.last_registered_id = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "pipeline_state" not in st.session_state:
    st.session_state.pipeline_state = None


# Render Header and Disclaimer
components.render_header()
components.render_disclaimer()

# Sidebar: System Status & Demo Controls
with st.sidebar:
    st.markdown("### 🏛️ System Operational Status")
    
    # Engine status indicator
    if vision.is_openai_configured():
        st.success(f"🟢 **AI Engine:** Online\nModel: `{OPENAI_MODEL}`")
    else:
        st.info("🟡 **AI Engine:** Offline / Local Fallback Active\n(Deterministic Agent + Heuristic Vision)")

    st.markdown("---")
    st.markdown("### 🔍 Quick Sample Demos")
    st.caption("Click to load pre-configured test scenarios:")

    sample_col1, sample_col2 = st.columns(2)
    sample_dir = Path(__file__).resolve().parent / "data" / "samples"

    if sample_col1.button("🕳️ Pothole", use_container_width=True):
        st.session_state.selected_sample = "sample_pothole.jpg"
        st.session_state.sample_hint = "Potholes and damaged roads"
        st.session_state.sample_city = "Bengaluru"
        st.session_state.sample_locality = "Indiranagar"
        st.rerun()

    if sample_col2.button("🗑️ Garbage", use_container_width=True):
        st.session_state.selected_sample = "sample_garbage.jpg"
        st.session_state.sample_hint = "Overflowing garbage"
        st.session_state.sample_city = "Mumbai"
        st.session_state.sample_locality = "Bandra West"
        st.rerun()

    sample_col3, sample_col4 = st.columns(2)
    if sample_col3.button("💡 Streetlight", use_container_width=True):
        st.session_state.selected_sample = "sample_streetlight.jpg"
        st.session_state.sample_hint = "Broken streetlights"
        st.session_state.sample_city = "Delhi"
        st.session_state.sample_locality = "Connaught Place"
        st.rerun()

    if sample_col4.button("🌊 Drainage", use_container_width=True):
        st.session_state.selected_sample = "sample_waterlogging.jpg"
        st.session_state.sample_hint = "Waterlogging and drainage issues"
        st.session_state.sample_city = "Ahmedabad"
        st.session_state.sample_locality = "Satellite"
        st.rerun()

    if st.button("🐱 Non-Civic Image (Pet)", use_container_width=True):
        st.session_state.selected_sample = "sample_non_civic.jpg"
        st.session_state.sample_hint = "Non-Civic"
        st.session_state.sample_city = "Pune"
        st.session_state.sample_locality = "Kothrud"
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Sample Tracking IDs")
    st.code("NS-DEMO-A101B202\nNS-DEMO-C303D404\nNS-DEMO-E505F606", language="text")

    st.markdown("---")
    st.caption("NazarSetu v1.0 • Hackathon MVP Edition")


# Main Tabs
tab_report, tab_track, tab_trail, tab_admin = st.tabs([
    "📸 Citizen Reporting Studio",
    "💬 Tracking Assistant",
    "⚡ Agent Action Trail",
    "⚙️ Demo Administration",
])


# ==============================================================================
# TAB 1: CITIZEN REPORTING STUDIO
# ==============================================================================
with tab_report:
    st.markdown("### 📝 Report a Civic Infrastructure Issue")
    st.write("Upload a photograph of a civic defect. Our autonomous AI agent will analyze visual evidence, determine ward jurisdiction, and route the issue to the appropriate department.")

    # Location Selection
    wards_df = pd.read_csv(DEMO_WARDS_CSV)
    cities = sorted(wards_df["city"].unique().tolist())

    col_loc1, col_loc2, col_loc3 = st.columns([1, 1, 1.5])
    
    default_city_idx = 0
    if "sample_city" in st.session_state and st.session_state.sample_city in cities:
        default_city_idx = cities.index(st.session_state.sample_city)

    with col_loc1:
        selected_city = st.selectbox("Select City", cities, index=default_city_idx)
    
    localities_for_city = sorted(wards_df[wards_df["city"] == selected_city]["locality"].unique().tolist())
    default_loc_idx = 0
    if "sample_locality" in st.session_state and st.session_state.sample_locality in localities_for_city:
        default_loc_idx = localities_for_city.index(st.session_state.sample_locality)

    with col_loc2:
        selected_locality = st.selectbox("Select Locality / Ward", localities_for_city, index=default_loc_idx)

    with col_loc3:
        landmark_input = st.text_input("Landmark or Street Description (Optional)", placeholder="e.g. Near Metro Pillar 104, Opposite ICICI Bank")

    # Image Upload & Preview
    col_img_up, col_img_prev = st.columns([1.2, 1])
    
    with col_img_up:
        uploaded_file = st.file_uploader(
            "Upload Evidence Photograph (JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            help="Take or upload a clear photo of the damaged road, garbage, streetlight, or drain."
        )

        # Check if sample was chosen
        image_bytes = None
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
        elif "selected_sample" in st.session_state:
            sample_path = sample_dir / st.session_state.selected_sample
            if sample_path.exists():
                with open(sample_path, "rb") as f:
                    image_bytes = f.read()
                st.info(f"Loaded Demo Sample: `{st.session_state.selected_sample}`")

    with col_img_prev:
        if image_bytes:
            st.image(image_bytes, caption="Uploaded Evidence Photograph", use_column_width=True)
            image_hash = tools.compute_image_hash(image_bytes)
            st.caption(f"SHA-256 Signature: `{image_hash[:20]}...`")
        else:
            st.markdown("""
                <div style="border: 2px dashed #CBD5E1; border-radius: 12px; padding: 40px; text-align: center; color: #94A3B8;">
                    📷 Photo preview will appear here.<br>Select a sample from the sidebar or upload an image.
                </div>
            """, unsafe_allow_html=True)

    # Analyze Button
    analyze_col1, analyze_col2 = st.columns([1, 3])
    with analyze_col1:
        analyze_clicked = st.button("🚀 Analyze Issue", type="primary", use_container_width=True, disabled=image_bytes is None)

    if analyze_clicked and image_bytes:
        with st.spinner("🤖 Autonomous AI Agent analyzing image and querying municipal registers..."):
            # Step 1: Vision Analysis
            hint = st.session_state.get("sample_hint")
            analysis = vision.analyze_issue(image_bytes, hint_category=hint)
            st.session_state.analysis_result = analysis

            # If not a supported civic issue
            if not analysis.get("is_civic_issue", True):
                st.error("🚫 **Unsupported Submission:** The AI analyzed the image and determined that it does not show a recognized municipal civic issue (e.g., potholes, garbage, streetlights, or drainage).")
                st.info("NazarSetu only processes public municipal infrastructure defects.")
                st.session_state.pipeline_state = None
            else:
                # Step 2: Run autonomous agent pipeline
                issue_type = analysis.get("issue_type")
                pipeline_state, trail = agent.run_reporting_agent_pipeline(
                    issue_type=issue_type,
                    city=selected_city,
                    locality=selected_locality,
                    image_hash=image_hash,
                    landmark=landmark_input,
                )
                pipeline_state["image_bytes"] = image_bytes
                pipeline_state["analysis"] = analysis
                st.session_state.pipeline_state = pipeline_state
                
                # Merge steps into global action trail
                for s in trail.get_steps():
                    st.session_state.action_trail.record_step(
                        tool_name=s["tool_name"],
                        title=s["title"],
                        explanation=s["explanation"],
                        input_args=s["input_args"],
                        output_result=s["output_result"],
                        status=s["status"],
                    )

    # Display Analysis Results & Confirmation if pipeline ran
    if st.session_state.pipeline_state:
        p_state = st.session_state.pipeline_state
        analysis = p_state.get("analysis", {})

        st.markdown("---")
        st.markdown("### 🧬 AI Inspection Output: Issue DNA")
        
        # Render Issue DNA Card
        components.render_issue_dna(
            dna_data=analysis,
            locality=p_state.get("locality"),
            city=p_state.get("city")
        )

        # Smart Duplicate Guard Alert
        dup_check = p_state.get("duplicate_check", {})
        if dup_check.get("is_duplicate"):
            dup_id = dup_check.get("existing_complaint_id")
            dup_status = dup_check.get("existing_status")
            st.warning(f"""
                ⚠️ **Smart Duplicate Guard Alert:** A potentially matching unresolved complaint (**{dup_id}**)
                already exists in **{p_state.get('locality')}** with status **{dup_status.upper()}**.
            """)
            dup_c1, dup_c2 = st.columns([1, 1.5])
            with dup_c1:
                if st.button(f"🔍 Track Existing Report ({dup_id})", use_container_width=True):
                    # Populate tracking chat
                    st.session_state.chat_messages.append({"role": "user", "content": f"Where is {dup_id}?"})
                    st.info(f"Switching to Tracking Assistant for {dup_id}...")
            with dup_c2:
                st.caption("Or verify below and proceed if this is an independent, distinct incident.")

        # Citizen Review & Correction Area
        st.markdown("#### ✏️ Citizen Review & Correction")
        st.caption("You have complete authority to inspect and override the AI's classification before official registration.")

        review_col1, review_col2, review_col3 = st.columns([1.5, 1, 1])
        with review_col1:
            corrected_category = st.selectbox(
                "Confirm / Correct Issue Category",
                SUPPORTED_CATEGORIES,
                index=SUPPORTED_CATEGORIES.index(p_state["issue_type"]) if p_state["issue_type"] in SUPPORTED_CATEGORIES else 0
            )
        with review_col2:
            corrected_priority = st.selectbox(
                "Priority Level",
                ["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(analysis.get("suggested_priority", "Medium"))
            )
        with review_col3:
            assigned_dept = tools.select_department(corrected_category).get("department")
            st.text_input("Assigned Department (Auto-Routed)", value=assigned_dept, disabled=True)

        corrected_desc = st.text_area(
            "Complaint Description",
            value=analysis.get("suggested_description", f"Civic issue reported in {p_state['locality']}."),
            rows=3
        )

        # Explicit Confirmation Requirement
        st.markdown("---")
        st.markdown("#### 🛡️ Final Registration Confirmation")
        confirm_checkbox = st.checkbox(
            "I explicitly confirm that the above details and photographic evidence represent an authentic civic issue.",
            value=False
        )

        submit_col1, submit_col2 = st.columns([1, 2])
        with submit_col1:
            register_btn = st.button("✅ Confirm & Register Complaint", type="primary", use_container_width=True, disabled=not confirm_checkbox)

        if register_btn:
            if not confirm_checkbox:
                st.error("Explicit citizen confirmation is required before submitting.")
            else:
                    uncertainties = analysis.get("uncertainty_flags", [])
                    uncertainty_str = "; ".join(uncertainties) if uncertainties else "No visual uncertainties flagged."
                    ai_mode_val = "AI_VERIFIED" if analysis.get("mode") == "openai_vision" else "FALLBACK_MANUAL"
                    
                    confirmed_payload = {
                        "confirmed": True,
                        "idempotency_key": database.generate_idempotency_key(p_state["image_hash"]),
                        "issue_type": corrected_category,
                        "description": corrected_desc,
                        "city": p_state["city"],
                        "locality": p_state["locality"],
                        "ward": p_state.get("ward", "Demo Ward"),
                        "department": assigned_dept,
                        "image_hash": p_state["image_hash"],
                        "priority": corrected_priority,
                        "status": STATUS_PENDING,
                        "landmark": p_state.get("landmark", ""),
                        "visual_evidence": analysis.get("visual_evidence"),
                        "uncertainty_notes": uncertainty_str,
                        "ai_mode": ai_mode_val,
                    }
                    reg_res, reg_trail = agent.run_registration_agent_action(confirmed_payload)
                    
                    # Log in action trail
                    for s in reg_trail.get_steps():
                        st.session_state.action_trail.record_step(
                            tool_name=s["tool_name"],
                            title=s["title"],
                            explanation=s["explanation"],
                            input_args=s["input_args"],
                            output_result=s["output_result"],
                            status=s["status"],
                        )

                    if reg_res.get("status") == "registered":
                        complaint_id = reg_res.get("complaint_id")
                        st.session_state.last_registered_id = complaint_id
                        st.success(f"🎉 **Complaint Successfully Registered!**")
                        st.balloons()
                        
                        st.markdown(f"""
                            <div class="nazar-card" style="border-left: 6px solid #10B981;">
                                <h3 style="margin-top: 0; color: #0F766E;">Official Municipal Tracking Pass</h3>
                                <p style="font-size: 1.2rem; font-weight: 700; color: #102A43;">
                                    Tracking ID: <code>{complaint_id}</code>
                                </p>
                                <p><strong>Assigned Department:</strong> {assigned_dept}<br>
                                <strong>Jurisdiction:</strong> {p_state.get('ward')} ({p_state.get('locality')}, {p_state.get('city')})<br>
                                <strong>Status:</strong> <span style="background-color: #FEF3C7; color: #D97706; padding: 3px 8px; border-radius: 4px; font-weight: 700;">PENDING</span></p>
                                <p style="font-size: 0.9rem; color: #64748B;">You can copy this ID to track real-time resolution progress in the <strong>Tracking Assistant</strong> tab.</p>
                            </div>
                        """, unsafe_allow_html=True)


# ==============================================================================
# TAB 2: COMPLAINT TRACKING ASSISTANT
# ==============================================================================
with tab_track:
    st.markdown("### 💬 Conversational Complaint Tracking Assistant")
    st.caption("Ask questions about registered complaints. The assistant retrieves live records directly from SQLite via real agent tool calling.")

    # Quick test pills
    st.markdown("**Quick Inquiries:**")
    pill_col1, pill_col2, pill_col3, pill_col4 = st.columns(4)
    quick_query = None

    with pill_col1:
        if st.button("Check NS-DEMO-A101B202", use_container_width=True):
            quick_query = "What is the status of complaint NS-DEMO-A101B202?"
    with pill_col2:
        if st.button("Check NS-DEMO-C303D404", use_container_width=True):
            quick_query = "Where is complaint NS-DEMO-C303D404 and who is handling it?"
    with pill_col3:
        if st.button("Check NS-DEMO-E505F606", use_container_width=True):
            quick_query = "Is streetlight complaint NS-DEMO-E505F606 resolved?"
    with pill_col4:
        if st.session_state.last_registered_id:
            if st.button(f"Check {st.session_state.last_registered_id}", use_container_width=True):
                quick_query = f"Track my recent complaint {st.session_state.last_registered_id}"
        else:
            if st.button("Ask without ID", use_container_width=True):
                quick_query = "Where is my complaint?"

    # Render Chat History
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "status" in msg:
                components.render_status_tracker(msg["status"])
            if "timeline" in msg and msg["timeline"]:
                with st.expander("📜 View Audit Timeline Events"):
                    for ev in msg["timeline"]:
                        st.markdown(f"- **{ev['created_at']}** — `[{ev['event_type']}]`: {ev['details']}")

    # Handle Input (either from quick pill or chat input)
    user_prompt = st.chat_input("Ask about a complaint (e.g. 'What is the status of NS-DEMO-A101B202?')")
    if quick_query:
        user_prompt = quick_query

    if user_prompt:
        # Display user message
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Agent processing
        with st.chat_message("assistant"):
            with st.spinner("🤖 Consulting municipal records via agent tool calls..."):
                response = agent.run_tracking_chat_agent(
                    user_message=user_prompt,
                    chat_history=st.session_state.chat_messages,
                    trail=st.session_state.action_trail,
                )
                
                reply_text = response.get("reply", "Unable to retrieve records.")
                st.markdown(reply_text)

                msg_record = {"role": "assistant", "content": reply_text}

                # If complaint record was fetched, render the 3-stage tracker
                if response.get("complaint_data"):
                    c_status = response["complaint_data"].get("current_status", "Pending")
                    components.render_status_tracker(c_status)
                    msg_record["status"] = c_status

                if response.get("timeline_data"):
                    events = response["timeline_data"]
                    msg_record["timeline"] = events
                    with st.expander("📜 View Audit Timeline Events"):
                        for ev in events:
                            st.markdown(f"- **{ev['created_at']}** — `[{ev['event_type']}]`: {ev['details']}")

                st.session_state.chat_messages.append(msg_record)


# ==============================================================================
# TAB 3: AGENT ACTION TRAIL
# ==============================================================================
with tab_trail:
    st.markdown("### ⚡ Live Autonomous Agent Action Trail")
    st.write("Verifiable step-by-step progress tracker of genuine model tool executions and database transactions.")

    top_c1, top_c2 = st.columns([3, 1])
    with top_c2:
        if st.button("🗑️ Clear Activity History"):
            st.session_state.action_trail.clear()
            st.rerun()

    components.render_action_trail(st.session_state.action_trail.get_steps())


# ==============================================================================
# TAB 4: DEMO ADMINISTRATION (COMMAND CENTER)
# ==============================================================================
with tab_admin:
    st.markdown("### ⚙️ Demo Administration Command Center")
    st.caption("Simulate municipal officer workflow: view incoming complaints, filter jurisdictions, and advance resolution stages.")

    # Counters
    stats = database.get_complaint_stats()
    components.render_stat_counters(stats)

    st.markdown("---")
    st.markdown("#### 🎛️ Filter Municipal Register")

    filt_c1, filt_c2, filt_c3 = st.columns(3)
    with filt_c1:
        issue_filter = st.selectbox("Filter by Category", ["All"] + SUPPORTED_CATEGORIES)
    with filt_c2:
        dept_filter = st.selectbox("Filter by Department", ["All"] + list(set(tools.DEPARTMENT_MAPPING.values())))
    with filt_c3:
        status_filter = st.selectbox("Filter by Status", ["All"] + VALID_STATUSES)

    complaints_list = database.list_complaints(
        issue_type=issue_filter,
        department=dept_filter,
        status=status_filter,
        limit=100
    )

    if not complaints_list:
        st.info("No complaints found matching the selected filters.")
    else:
        # Display Table
        df_display = pd.DataFrame(complaints_list)
        df_view = df_display[[
            "id", "issue_type", "city", "locality", "department", "priority", "status", "created_at"
        ]].rename(columns={
            "id": "Tracking ID",
            "issue_type": "Category",
            "city": "City",
            "locality": "Locality",
            "department": "Department",
            "priority": "Priority",
            "status": "Status",
            "created_at": "Logged At",
        })
        st.dataframe(df_view, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🛠️ Update Complaint Status (Demo Dispatch)")
        st.caption("Change a status here to see it update immediately in the conversational Tracking Assistant!")

        up_col1, up_col2, up_col3 = st.columns([1.5, 1.2, 2])
        
        cid_options = [c["id"] for c in complaints_list]
        with up_col1:
            target_cid = st.selectbox("Select Complaint to Update", cid_options)

        target_obj = next((c for c in complaints_list if c["id"] == target_cid), None)
        curr_status_val = target_obj["status"] if target_obj else STATUS_PENDING

        with up_col2:
            next_status = st.selectbox("New Operational Status", VALID_STATUSES, index=VALID_STATUSES.index(curr_status_val))

        with up_col3:
            status_note = st.text_input("Operational Reason / Crew Note", placeholder="e.g. Field crew dispatched with cold asphalt mix.")

        if st.button("🚀 Apply Status Change", type="primary"):
            success = database.update_complaint_status(
                complaint_id=target_cid,
                new_status=next_status,
                note=status_note
            )
            if success:
                st.success(f"Status for **{target_cid}** updated to **{next_status.upper()}**!")
                # Add action to trail
                st.session_state.action_trail.record_step(
                    tool_name="update_complaint_status",
                    title=f"Admin Status Change: {target_cid}",
                    explanation=f"Municipal status transitioned from '{curr_status_val}' to '{next_status}'. Note: {status_note}",
                    input_args={"complaint_id": target_cid, "new_status": next_status, "note": status_note},
                    output_result={"success": True, "updated_status": next_status},
                    status="success"
                )
                st.rerun()
            else:
                st.error("Failed to update status. Invalid complaint ID or status value.")

        # Show selected complaint timeline
        if target_cid:
            with st.expander(f"📜 View Full Event Audit Log for {target_cid}"):
                evs = database.get_complaint_timeline(target_cid)
                for e in evs:
                    st.markdown(f"- **{e['created_at']}** — `[{e['event_type']}]`: {e['details']}")
