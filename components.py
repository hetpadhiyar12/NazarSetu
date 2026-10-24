"""
NazarSetu Reusable UI Components & Styling.

Provides custom CSS, Issue DNA cards, Agent Action Trail timelines,
and 3-stage status trackers matching the Indian civic-tech visual design system.
"""

import json
from typing import Dict, Any, List, Optional
import streamlit as st
from config import CATEGORY_METADATA, DEMO_DISCLAIMER


CUSTOM_CSS = """
<style>
/* NazarSetu Indian Civic-Tech Design System */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --navy-dark: #102A43;
    --navy-mid: #243B53;
    --navy-light: #334E68;
    --teal-primary: #16A6A0;
    --teal-light: #E6FFFA;
    --teal-dark: #0F766E;
    --saffron: #F4A340;
    --saffron-light: #FEF3C7;
    --ivory-bg: #F8FAFC;
    --card-bg: #FFFFFF;
    --text-primary: #0F172A;
    --text-secondary: #475569;
    --border-color: #E2E8F0;
    --status-pending: #F59E0B;
    --status-progress: #3B82F6;
    --status-resolved: #10B981;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
}

/* Header Branding */
.nazar-header {
    background: linear-gradient(135deg, #102A43 0%, #164E63 100%);
    padding: 1.8rem 2.2rem;
    border-radius: 16px;
    color: white;
    box-shadow: 0 10px 25px -5px rgba(16, 42, 67, 0.25);
    margin-bottom: 1.5rem;
    border-left: 6px solid var(--saffron);
}

.nazar-title {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}

.nazar-tagline {
    font-size: 1.05rem;
    font-weight: 600;
    color: #F4A340;
    margin: 4px 0 8px 0;
    letter-spacing: 0.02em;
}

.nazar-subtitle {
    font-size: 0.95rem;
    color: #CBD5E1;
    margin: 0;
    line-height: 1.4;
}

/* Disclaimer pill */
.disclaimer-banner {
    background-color: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: #1E40AF;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1.5rem;
}

/* Card Styling */
.nazar-card {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 1.4rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    margin-bottom: 1.2rem;
    transition: all 0.2s ease;
}

.nazar-card:hover {
    box-shadow: 0 8px 16px -2px rgba(16, 42, 67, 0.08);
}

/* Issue DNA Card */
.issue-dna-card {
    background: linear-gradient(to bottom right, #FFFFFF, #F8FAFC);
    border: 2px solid #16A6A0;
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 10px 30px rgba(22, 166, 160, 0.1);
    margin-top: 1rem;
    margin-bottom: 1.5rem;
}

.dna-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 12px;
    margin-bottom: 16px;
}

.dna-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #102A43;
    display: flex;
    align-items: center;
    gap: 8px;
}

.dna-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.badge-high { background-color: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; }
.badge-medium { background-color: #FEF3C7; color: #D97706; border: 1px solid #FCD34D; }
.badge-low { background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }

.dna-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
}

.dna-item {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px;
}

.dna-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.dna-value {
    font-size: 0.95rem;
    font-weight: 600;
    color: #0F172A;
}

/* Action Trail Styling */
.trail-step {
    border-left: 3px solid #16A6A0;
    padding-left: 18px;
    margin-bottom: 18px;
    position: relative;
}

.trail-step::before {
    content: '';
    position: absolute;
    left: -7px;
    top: 4px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: #16A6A0;
    border: 2px solid white;
    box-shadow: 0 0 0 2px #16A6A0;
}

.trail-step.warning {
    border-left-color: #F59E0B;
}
.trail-step.warning::before {
    background-color: #F59E0B;
    box-shadow: 0 0 0 2px #F59E0B;
}

.trail-step.error {
    border-left-color: #EF4444;
}
.trail-step.error::before {
    background-color: #EF4444;
    box-shadow: 0 0 0 2px #EF4444;
}

.step-meta {
    font-size: 0.78rem;
    color: #64748B;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 2px;
}

.step-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #102A43;
    margin-bottom: 3px;
}

.step-expl {
    font-size: 0.85rem;
    color: #475569;
    margin-bottom: 6px;
}

.step-output {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    color: #334155;
    white-space: pre-wrap;
    word-break: break-all;
}

/* Status Tracker 3-Stage */
.status-tracker {
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    margin: 20px 0 25px 0;
    padding: 0 15px;
}

.status-tracker::before {
    content: '';
    position: absolute;
    top: 15px;
    left: 45px;
    right: 45px;
    height: 3px;
    background-color: #E2E8F0;
    z-index: 1;
}

.stage-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    z-index: 2;
}

.node-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background-color: white;
    border: 3px solid #CBD5E1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748B;
    margin-bottom: 6px;
    transition: all 0.3s;
}

.stage-node.active .node-circle {
    border-color: #16A6A0;
    background-color: #16A6A0;
    color: white;
    box-shadow: 0 0 0 4px rgba(22, 166, 160, 0.2);
}

.stage-node.completed .node-circle {
    border-color: #10B981;
    background-color: #10B981;
    color: white;
}

.node-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
}

.stage-node.active .node-label {
    color: #16A6A0;
    font-weight: 700;
}

.stage-node.completed .node-label {
    color: #10B981;
}

/* Metric Counter Cards */
.stat-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.stat-num {
    font-size: 2rem;
    font-weight: 800;
    color: #102A43;
    line-height: 1;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
</style>
"""


import textwrap


def render_html(html_str: str):
    """Safely dedent and render HTML in Streamlit without triggering Markdown indented code block formatting."""
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)


def render_header():
    """Renders the top branding and hackathon banner."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_html("""
        <div class="nazar-header">
            <div class="nazar-title">
                <span>🛡️ NazarSetu</span>
            </div>
            <div class="nazar-tagline">See the Problem. Bridge to Action.</div>
            <div class="nazar-subtitle">
                From a single photograph to meaningful civic action — powered by autonomous AI agents.
            </div>
        </div>
    """)


def render_disclaimer():
    """Renders the hackathon prototype disclaimer banner."""
    render_html(f"""
        <div class="disclaimer-banner">
            <span>ℹ️</span>
            <div><strong>Hackathon MVP Demonstration:</strong> {DEMO_DISCLAIMER}</div>
        </div>
    """)


def render_issue_dna(dna_data: Dict[str, Any], locality: str = "", city: str = ""):
    """Renders the structured Issue DNA summary card."""
    problem = dna_data.get("issue_type", "Unknown Civic Issue")
    evidence = dna_data.get("visual_evidence", "No evidence analyzed.")
    priority = dna_data.get("suggested_priority", "Medium")
    action = dna_data.get("recommended_action", "Register complaint with civic authorities.")
    uncertainties = dna_data.get("uncertainty_flags", [])
    confidence = dna_data.get("confidence_score", 0.90)

    # Determine priority badge class
    p_lower = priority.lower()
    if "high" in p_lower:
        badge_class = "badge-high"
    elif "low" in p_lower:
        badge_class = "badge-low"
    else:
        badge_class = "badge-medium"

    # Meta icon
    meta = CATEGORY_METADATA.get(problem, {"icon": "📍", "color": "#16A6A0"})

    location_str = f"{locality}, {city}" if (locality and city) else "Locality Selected"

    uncertainty_html = ""
    if uncertainties:
        uncertainty_html = f"""<div style="margin-top: 12px; background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 8px; padding: 8px 12px; font-size: 0.82rem; color: #92400E;">⚠️ <strong>Uncertainty / Notice:</strong> {' • '.join(uncertainties)}</div>"""

    html = f"""
    <div class="issue-dna-card">
        <div class="dna-header">
            <div class="dna-title">
                <span>{meta['icon']} Issue DNA</span>
                <span style="font-size: 0.85rem; font-weight: 500; color: #64748B; margin-left: 8px;">Confidence: {int(confidence*100)}%</span>
            </div>
            <span class="dna-badge {badge_class}">{priority} Priority</span>
        </div>
        <div class="dna-grid">
            <div class="dna-item">
                <div class="dna-label">Problem Identified</div>
                <div class="dna-value">{problem}</div>
            </div>
            <div class="dna-item">
                <div class="dna-label">Assigned Location</div>
                <div class="dna-value">{location_str}</div>
            </div>
            <div class="dna-item" style="grid-column: span 2;">
                <div class="dna-label">Visible Evidence</div>
                <div class="dna-value" style="font-size: 0.88rem; font-weight: 500; color: #334155; line-height: 1.4;">
                    {evidence}
                </div>
            </div>
            <div class="dna-item" style="grid-column: span 2;">
                <div class="dna-label">Recommended Action</div>
                <div class="dna-value" style="font-size: 0.88rem; font-weight: 600; color: #0F766E;">
                    {action}
                </div>
            </div>
        </div>
        {uncertainty_html}
    </div>
    """
    render_html(html)


def render_action_trail(steps: List[Dict[str, Any]]):
    """Renders the Agent Action Trail vertical progress tracker."""
    if not steps:
        st.info("No autonomous actions recorded yet.")
        return

    st.markdown("### ⚡ Agent Action Trail")
    st.caption("Verifiable real-time event log generated from genuine Python tool executions.")

    for step in steps:
        status = step.get("status", "success")
        tool_name = step.get("tool_name", "tool")
        title = step.get("title", tool_name)
        expl = step.get("explanation", "")
        timestamp = step.get("timestamp", "")
        output_result = step.get("output_result", {})

        icon = "✅"
        if status == "warning":
            icon = "⚠️"
        elif status == "error":
            icon = "❌"

        formatted_output = json.dumps(output_result, indent=2) if isinstance(output_result, (dict, list)) else str(output_result)

        step_html = f"""
        <div class="trail-step {status}">
            <div class="step-meta">STEP {step.get('step_number', 1)} • {timestamp} • <code>{tool_name}()</code></div>
            <div class="step-title">{icon} {title}</div>
            <div class="step-expl">{expl}</div>
        </div>
        """
        render_html(step_html)
        with st.expander(f"Inspect Tool Execution Payload: `{tool_name}()`"):
            st.code(formatted_output, language="json")


def render_status_tracker(current_status: str):
    """Renders the 3-stage status tracker: Pending -> In Progress -> Resolved."""
    status_clean = current_status.strip().title()

    is_pending_done = status_clean in ["Pending", "In Progress", "Resolved"]
    is_pending_active = status_clean == "Pending"

    is_progress_done = status_clean in ["In Progress", "Resolved"]
    is_progress_active = status_clean == "In Progress"

    is_resolved_done = status_clean == "Resolved"
    is_resolved_active = status_clean == "Resolved"

    def get_classes(is_active, is_done):
        if is_active:
            return "stage-node active"
        if is_done:
            return "stage-node completed"
        return "stage-node"

    c1 = get_classes(is_pending_active, is_pending_done)
    c2 = get_classes(is_progress_active, is_progress_done)
    c3 = get_classes(is_resolved_active, is_resolved_done)

    html = f"""
    <div class="status-tracker">
        <div class="{c1}">
            <div class="node-circle">{'✓' if (is_progress_done and not is_pending_active) else '1'}</div>
            <div class="node-label">Pending</div>
        </div>
        <div class="{c2}">
            <div class="node-circle">{'✓' if (is_resolved_done and not is_progress_active) else '2'}</div>
            <div class="node-label">In Progress</div>
        </div>
        <div class="{c3}">
            <div class="node-circle">{'✓' if is_resolved_active else '3'}</div>
            <div class="node-label">Resolved</div>
        </div>
    </div>
    """
    render_html(html)


def render_stat_counters(stats: Dict[str, int]):
    """Renders 4 metric cards for the Admin Dashboard."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_html(f"""
            <div class="stat-card">
                <div class="stat-num">{stats.get('total', 0)}</div>
                <div class="stat-label">Total Reports</div>
            </div>
        """)
    with col2:
        render_html(f"""
            <div class="stat-card" style="border-top: 4px solid #F59E0B;">
                <div class="stat-num" style="color: #D97706;">{stats.get('pending', 0)}</div>
                <div class="stat-label">Pending Action</div>
            </div>
        """)
    with col3:
        render_html(f"""
            <div class="stat-card" style="border-top: 4px solid #3B82F6;">
                <div class="stat-num" style="color: #2563EB;">{stats.get('in_progress', 0)}</div>
                <div class="stat-label">In Progress</div>
            </div>
        """)
    with col4:
        render_html(f"""
            <div class="stat-card" style="border-top: 4px solid #10B981;">
                <div class="stat-num" style="color: #059669;">{stats.get('resolved', 0)}</div>
                <div class="stat-label">Resolved</div>
            </div>
        """)

