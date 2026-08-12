from __future__ import annotations

from datetime import date, timedelta
from html import escape
import os
import re

import requests
import streamlit as st


st.set_page_config(
    page_title="NeuroGuard AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 1.4rem; padding-bottom: 4rem; }
    .hero { padding: 1.6rem 1.8rem; border-radius: 1.2rem; background: linear-gradient(135deg, #e6f7f7, #f8fcfc); border: 1px solid #a9dfe0; box-shadow: 0 8px 24px rgba(18, 61, 74, .08); }
    .hero h1 { margin: 0 0 .35rem 0; color: #123d4a; letter-spacing: -.02em; }
    .hero p { color: #315965; margin: .3rem 0; }
    .section-kicker { color: #2b7a7b; text-transform: uppercase; letter-spacing: .08em; font-size: .76rem; font-weight: 800; margin-top: 1.3rem; }
    .quick-card { padding: .85rem 1rem; border-radius: .8rem; border: 1px solid #d5e3e6; background: rgba(255,255,255,.72); min-height: 6.3rem; }
    .quick-card strong { color: #123d4a; }
    .muted { color: #52666d; font-size: .92rem; }
    .emergency { padding: 1.1rem 1.2rem; border-radius: 1rem; background: #fff0f0; border: 2px solid #d43d3d; color: #6f1111; box-shadow: 0 6px 18px rgba(212,61,61,.12); }
    .disclaimer { padding: .9rem 1rem; border-left: 4px solid #2ca6a4; background: #f2f8f8; border-radius: .3rem; }
    [data-testid="stForm"] { border: 1px solid #d5e3e6; border-radius: 1rem; padding: 1rem 1.1rem .8rem; background: rgba(255,255,255,.35); }
    [data-testid="stMetricValue"] { letter-spacing: -.03em; }
    .trajectory { display: flex; gap: .55rem; overflow-x: auto; padding: .8rem .2rem 1rem; }
    .trajectory-item { min-width: 8.2rem; padding: .8rem; border-radius: .85rem; border: 1px solid #d5e3e6; background: #fff; box-shadow: 0 3px 10px rgba(18,61,74,.06); }
    .trajectory-day { font-size: 1.1rem; font-weight: 800; color: #123d4a; }
    .trajectory-status { display: inline-block; margin-top: .45rem; padding: .2rem .45rem; border-radius: 999px; font-size: .74rem; font-weight: 800; letter-spacing: .03em; }
    .trajectory-meta { color: #52666d; font-size: .82rem; margin-top: .2rem; }
    .trajectory-low { border-top: 4px solid #2ca66f; }
    .trajectory-low .trajectory-status { background: #d7f2e4; color: #155b39; }
    .trajectory-moderate { border-top: 4px solid #e2a52e; }
    .trajectory-moderate .trajectory-status { background: #fff1cf; color: #7b5200; }
    .trajectory-high { border-top: 4px solid #d43d3d; }
    .trajectory-high .trajectory-status { background: #ffe0e0; color: #7a1616; }
    </style>
    """,
    unsafe_allow_html=True,
)


STAGE_NAMES = {
    1: "Relative rest & evaluation",
    2: "Return to learning",
    3: "Symptom-limited aerobic activity",
    4: "Work/sport-specific activity",
    5: "Full return with monitoring",
}

STAGE_CONTEXT = {
    1: "Prioritize relative rest, sleep, professional evaluation, and avoiding re-injury.",
    2: "Use short, tolerable school or work periods with breaks and temporary accommodations.",
    3: "Increase light aerobic activity gradually and pause if symptoms meaningfully worsen.",
    4: "Reintroduce demanding non-contact work or sport-specific activity in small steps.",
    5: "Return fully only when symptoms remain controlled at rest and with exertion; continue monitoring.",
}


def validate_result(result: dict) -> tuple[bool, str]:
    """Guard the UI against recovery-service schema drift."""
    required = {"symptoms", "risk", "plan", "explanation", "safety"}
    if set(result) != required:
        return False, "The backend returned an unexpected response shape."
    if not isinstance(result["explanation"], str) or not result["explanation"].strip():
        return False, "The backend returned an empty explanation."
    plan = result["plan"]
    try:
        stage = int(plan.get("stage", 0)) if isinstance(plan, dict) else 0
    except (TypeError, ValueError):
        stage = 0
    if not isinstance(plan, dict) or not 1 <= stage <= 5:
        return False, "The backend returned an invalid recovery stage."
    recommendations = plan.get("recommendations")
    if not isinstance(recommendations, list) or len(recommendations) != 3 or not all(isinstance(item, str) for item in recommendations):
        return False, "The backend returned an invalid recovery plan."
    safety = result["safety"]
    if not isinstance(safety, dict) or set(safety) != {"safe", "alert"}:
        return False, "The backend returned an invalid safety result."
    return True, ""


def format_source(source: str) -> str:
    match = re.search(r"^(.*) Source: (https?://\S+)$", source)
    if not match:
        return source
    return f"{match.group(1)} ([open source]({match.group(2)}))"


def render_plan(plan: dict) -> None:
    st.subheader("Recovery plan")
    stage = int(plan["stage"])
    stage_name = STAGE_NAMES.get(stage, "Recovery stage")
    columns = st.columns(5)
    for index, column in enumerate(columns, start=1):
        with column:
            marker = "●" if index == stage else "○"
            st.markdown(f"### {marker} {index}")
            st.caption(STAGE_NAMES.get(index, "Recovery stage"))
    st.progress(stage / 5, text=f"Stage {stage} of 5 — {stage_name}")
    st.info(f"**Why this stage:** {STAGE_CONTEXT.get(stage, 'Progress gradually and follow professional guidance.')}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Recommended now**")
        for item in plan["recommendations"]:
            st.markdown(f"- {item}")
        st.markdown("**Monitor**")
        for item in plan.get("monitoring", ["Track symptoms and note any worsening."]):
            st.markdown(f"- {item}")
    with right:
        st.markdown("**Avoid or restrict**")
        for item in plan.get("restrictions", ["Avoid progressing if symptoms return or worsen."]):
            st.markdown(f"- {item}")
        st.markdown("**Escalate if**")
        st.warning(plan.get("escalation", "Follow the safety alert and seek professional guidance if symptoms worsen."))


def render_evidence(plan: dict, explanation: str) -> None:
    with st.expander("Evidence behind this plan", expanded=False):
        sources = plan.get("source_guidelines", [])
        if not sources:
            urls = re.findall(r"https?://[^\s|]+", explanation)
            if urls:
                st.write("The unified explanation used these evidence sources:")
                for url in dict.fromkeys(urls):
                    st.markdown(f"- [{url}]({url})")
            else:
                st.write("Evidence sources were included in the unified explanation returned by the backend.")
        for source in sources:
            st.markdown(f"- {format_source(source)}")


def render_handoff(result: dict) -> None:
    symptoms = result["symptoms"]
    risk = result["risk"]
    plan = result["plan"]
    stage = int(plan["stage"])
    stage_name = STAGE_NAMES.get(stage, "Recovery stage")
    summary = (
        f"NeuroGuard AI check-in\\n"
        f"Risk: {risk['risk_level'].upper()} ({risk['score']}/100)\\n"
        f"Recovery stage: {stage} — {stage_name}\\n"
        f"Risk factors: {', '.join(risk.get('factors', [])) or 'see unified risk assessment'}\\n"
        f"Symptoms detected: {symptoms.get('headache', 0)}/10 headache; dizziness={symptoms.get('dizziness', False)}\\n"
        f"Next steps: {'; '.join(plan['recommendations'])}\\n"
        f"Escalation: {plan.get('escalation', result['safety'].get('alert') or 'Seek professional guidance if symptoms worsen.')}\\n"
        "This is decision support, not a diagnosis or replacement for professional care."
    )
    with st.expander("Caregiver / clinician handoff summary", expanded=False):
        st.code(summary, language="text")
        st.download_button(
            "Download handoff summary",
            summary,
            file_name="neuroguard-handoff.txt",
            mime="text/plain",
        )


def render_detected_signals(symptoms: dict) -> None:
    detected: list[str] = []
    headache = int(symptoms.get("headache", 0) or 0)
    if headache:
        detected.append(f"headache {headache}/10")
    if symptoms.get("dizziness"):
        detected.append("dizziness")
    if symptoms.get("fatigue") in {"medium", "high"}:
        detected.append(f"{symptoms['fatigue']} fatigue")
    if symptoms.get("sleep_quality") == "poor":
        detected.append("poor sleep")
    if symptoms.get("mood") in {"anxious", "depressed"}:
        detected.append(symptoms["mood"])
    st.write(", ".join(detected) if detected else "No directly detected symptoms in the structured result.")


def render_trajectory(timeline: list[dict]) -> None:
    """Show the recovery story without requiring a charting dependency."""
    if not timeline:
        return

    ordered = sorted(enumerate(timeline), key=lambda item: (item[1].get("day", 0), item[0]))
    points = [item for _, item in ordered]
    latest = points[-1]
    latest_score = float(latest.get("score", 0))
    st.subheader("Recovery trajectory")

    if len(points) >= 2:
        first_score = float(points[0].get("score", 0))
        delta = latest_score - first_score
        if delta < 0:
            direction = f"Improving: risk score {first_score:g} → {latest_score:g}."
        elif delta > 0:
            direction = f"Worsening: risk score {first_score:g} → {latest_score:g}."
        else:
            direction = f"Stable: risk score remains {latest_score:g}."
        st.caption(direction + " Progress only while symptoms remain controlled.")
    else:
        st.caption("One check-in recorded. Add another check-in to see whether recovery is improving, stable, or worsening.")

    st.progress(
        max(0.0, min(1.0, latest_score / 100)),
        text=f"Current risk score: {latest_score:g}/100 · Recovery day {latest.get('day', 0)}",
    )

    cards: list[str] = []
    for point in points:
        risk_level = str(point.get("risk_level", "unknown")).lower()
        risk_class = risk_level if risk_level in {"low", "moderate", "high"} else "moderate"
        day_value = escape(str(point.get("day", 0)))
        stage = point.get("stage")
        stage_label = f"Stage {escape(str(stage))}" if stage else "Check-in"
        cards.append(
            f'<div class="trajectory-item trajectory-{risk_class}" '
            f'aria-label="Recovery day {day_value}, {risk_level} risk, {stage_label}">'
            f'<div class="trajectory-day">Day {day_value}</div>'
            f'<div class="trajectory-status">{escape(risk_level.upper())}</div>'
            f'<div class="trajectory-meta">{stage_label}</div>'
            "</div>"
        )
    st.markdown('<div class="trajectory">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    # Keep the underlying data visible for screen readers and precise review.
    table_rows = [
        {
            "Check-in date": point.get("checkin_date", "—"),
            "Recovery day": point.get("day", 0),
            "Risk score": point.get("score", 0),
            "Risk level": str(point.get("risk_level", "unknown")).upper(),
            "Stage": point.get("stage", "—"),
        }
        for point in points
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)


st.markdown(
    '<div class="hero"><h1>🧠 NeuroGuard AI</h1>'
    '<p class="muted">A privacy-conscious, evidence-grounded concussion recovery companion.</p>'
    "<p><strong>A calmer way to record symptoms, understand today’s next step, and notice when recovery needs professional attention.</strong></p></div>",
    unsafe_allow_html=True,
)

st.markdown('<div class="section-kicker">A simple three-step check-in</div>', unsafe_allow_html=True)
quick_left, quick_middle, quick_right = st.columns(3)
with quick_left:
    st.markdown('<div class="quick-card"><strong>1 · Describe</strong><br><span class="muted">Write what changed today, in your own words.</span></div>', unsafe_allow_html=True)
with quick_middle:
    st.markdown('<div class="quick-card"><strong>2 · Clarify</strong><br><span class="muted">Use optional selections for severity, trend, and warning signs.</span></div>', unsafe_allow_html=True)
with quick_right:
    st.markdown('<div class="quick-card"><strong>3 · Understand</strong><br><span class="muted">Review a conservative plan, evidence, and safety guidance.</span></div>', unsafe_allow_html=True)

if "timeline" not in st.session_state:
    st.session_state.timeline = []
if "next_recovery_day" not in st.session_state:
    st.session_state.next_recovery_day = 1
if "timeline_start_date" not in st.session_state:
    st.session_state.timeline_start_date = date.today()

with st.sidebar:
    st.header("Check-in settings")
    st.metric("Next check-in", f"Day {st.session_state.next_recovery_day}")
    st.caption("Each successful check-in advances the recovery timeline automatically. Previous check-ins remain visible below.")
    if st.button("Start new recovery timeline", type="secondary", use_container_width=True):
        st.session_state.timeline = []
        st.session_state.pop("latest", None)
        st.session_state.next_recovery_day = 1
        st.session_state.timeline_start_date = date.today()
        st.rerun()
    st.caption("Use this for a new person or injury. It clears this browser session’s stored check-ins, resets the timeline date, and starts again at Day 1.")
    st.divider()
    st.caption("Privacy: symptom text is sent to the configured backend. The backend redacts raw text from logs by default.")

structured_answers: dict = {}
with st.form("check_in_form", clear_on_submit=False):
    with st.expander("Optional guided questions", expanded=True):
        st.caption("Nothing is sent until you press Analyze check-in. Choose only what you know.")
        question_left, question_middle, question_right = st.columns(3)
        with question_left:
            headache_level = st.selectbox("Headache today", ["Not answered", *range(0, 11)], help="0 means no headache; 10 is the worst headache you can imagine.")
            dizziness = st.selectbox("Dizziness or balance trouble", ["Not answered", "No", "Yes"])
            fatigue = st.selectbox("Fatigue level", ["Not answered", "low", "medium", "high"])
        with question_middle:
            sleep_quality = st.selectbox("Sleep quality", ["Not answered", "good", "poor"])
            mood = st.selectbox("Mood", ["Not answered", "calm", "anxious", "depressed"])
            symptom_change = st.selectbox("Compared with the last check-in", ["Not answered", "improving", "stable", "worsening"])
        with question_right:
            activity_response = st.selectbox("Response to activity", ["Not answered", "tolerated", "worsened", "not_tried"])
            vomiting = st.selectbox("Vomiting", ["Not answered", "none", "once", "repeated"])
            emergency_labels = {
                "Seizure or convulsion": "seizure",
                "Loss of consciousness": "loss_of_consciousness",
                "Confusion or disorientation": "confusion",
                "Slurred speech": "slurred_speech",
                "Weakness or numbness": "weakness_or_numbness",
                "Unequal pupils or double vision": "unequal_pupils",
                "Unable to wake or stay awake": "unable_to_wake",
                "Repeated vomiting": "repeated_vomiting",
            }
            selected_emergency = st.multiselect("Urgent warning signs", list(emergency_labels), help="Select any that are present now. The safety layer will prioritize urgent escalation.")
        if headache_level != "Not answered":
            structured_answers["headache_level"] = int(headache_level)
        if dizziness != "Not answered":
            structured_answers["dizziness"] = dizziness == "Yes"
        for key, value in (("fatigue", fatigue), ("sleep_quality", sleep_quality), ("mood", mood), ("symptom_change", symptom_change), ("activity_response", activity_response), ("vomiting", vomiting)):
            if value != "Not answered":
                structured_answers[key] = value
        if selected_emergency:
            structured_answers["emergency_signs"] = [emergency_labels[label] for label in selected_emergency]

    input_text = st.text_area(
        "Daily symptom check-in",
        placeholder="Example: Mild headache after 20 minutes of schoolwork; walking felt okay.",
        height=130,
        help="Describe what changed today, what activity you tried, and whether symptoms improved or worsened.",
    )
    st.caption("You can use the written description, the guided questions, or both.")
    submitted = st.form_submit_button("Analyze check-in", type="primary", use_container_width=True)

if submitted:
    if not input_text.strip() and not structured_answers:
        st.warning("Add a written check-in or answer at least one structured question.")
    else:
        try:
            day = int(st.session_state.next_recovery_day)
            history = [
                {"day": item["day"], "score": item["score"], "risk_level": item["risk_level"]}
                for item in st.session_state.timeline
            ]
            response = requests.post(
                f"{os.getenv('NEUROGUARD_BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')}/analyze",
                json={"input_text": input_text, "day": int(day), "history": history, "structured_answers": structured_answers},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            valid, validation_message = validate_result(result)
            if not valid:
                st.error(validation_message)
                st.stop()
            st.session_state.latest = result
            timeline_entry = {
                "checkin_date": (st.session_state.timeline_start_date + timedelta(days=day - 1)).isoformat(),
                "day": int(day),
                "score": result["risk"]["score"],
                "risk_level": result["risk"]["risk_level"],
                "stage": result["plan"]["stage"],
            }
            st.session_state.timeline.append(timeline_entry)
            st.session_state.next_recovery_day = day + 1
            st.rerun()
        except requests.RequestException as error:
            st.error(f"Could not reach the backend: {error}")

result = st.session_state.get("latest")
if result:
    safe = result["safety"]
    if safe.get("alert"):
        st.markdown(
            f'<div class="emergency"><strong>Emergency warning</strong><br>{safe["alert"]}</div>',
            unsafe_allow_html=True,
        )
    elif not safe["safe"]:
        st.error("The safety layer blocked unsafe content. Seek guidance from a qualified professional.")

    st.subheader("Today’s assessment")
    metric_left, metric_middle, metric_right = st.columns(3)
    with metric_left:
        st.metric("Risk level", result["risk"]["risk_level"].upper())
    with metric_middle:
        st.metric("Risk score", f"{result['risk']['score']}/100")
    with metric_right:
        st.metric("Recovery stage", f"{result['plan']['stage']}/5")
    render_trajectory(st.session_state.timeline)

    plan_left, plan_right = st.columns([1.5, 1])
    with plan_left:
        render_plan(result["plan"])
    with plan_right:
        st.subheader("Why this result?")
        st.write(result["explanation"])
        st.markdown("**Signals detected**")
        render_detected_signals(result["symptoms"])

    render_evidence(result["plan"], result["explanation"])
    render_handoff(result)
    st.markdown(
        '<div class="disclaimer"><strong>Safety notice:</strong> '
        'This educational tool does not diagnose, treat, or replace professional medical care. '
        'Seek urgent help for severe or rapidly worsening symptoms.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Enter a daily check-in above to generate an evidence-grounded recovery view.")
