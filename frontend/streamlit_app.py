from __future__ import annotations

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
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .hero { padding: 1.4rem 1.6rem; border-radius: 1rem; background: linear-gradient(135deg, #e8f7f7, #f7fbfb); border: 1px solid #b8e1e1; }
    .hero h1 { margin-bottom: .25rem; color: #123d4a; }
    .stage-card { padding: 1rem; border-radius: .8rem; border: 1px solid #d5e3e6; background: #fff; min-height: 8rem; }
    .muted { color: #52666d; font-size: .92rem; }
    .emergency { padding: 1rem; border-radius: .8rem; background: #fff0f0; border: 2px solid #d43d3d; color: #6f1111; }
    .disclaimer { padding: .85rem 1rem; border-left: 4px solid #2ca6a4; background: #f2f8f8; }
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
    """Guard the UI against backend/provider schema drift."""
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


st.markdown(
    '<div class="hero"><h1>🧠 NeuroGuard AI</h1>'
    '<p class="muted">A privacy-conscious, evidence-grounded concussion recovery companion.</p>'
    "<p><strong>Use this to organize a check-in, not to diagnose or replace professional care.</strong></p></div>",
    unsafe_allow_html=True,
)

if "timeline" not in st.session_state:
    st.session_state.timeline = []

with st.sidebar:
    st.header("Check-in settings")
    api_url = st.text_input("Backend URL", "http://127.0.0.1:8000")
    day = st.number_input("Recovery day", min_value=0, max_value=3650, value=1, step=1)
    st.caption("Use the day after injury to make stage guidance longitudinal.")
    if st.button("Clear local timeline"):
        st.session_state.timeline = []
        st.rerun()
    st.divider()
    st.caption("Privacy: symptom text is sent to the configured backend. The backend redacts raw text from logs by default.")

input_text = st.text_area(
    "Daily symptom check-in",
    placeholder="Example: Mild headache after 20 minutes of schoolwork; walking felt okay.",
    height=130,
    help="Describe what changed today, what activity you tried, and whether symptoms improved or worsened.",
)

if st.button("Analyze check-in", type="primary", use_container_width=True):
    if not input_text.strip():
        st.warning("Enter a symptom check-in first.")
    else:
        try:
            history = [
                {"day": item["day"], "score": item["score"], "risk_level": item["risk_level"]}
                for item in st.session_state.timeline
            ]
            response = requests.post(
                f"{api_url.rstrip('/')}/analyze",
                json={"input_text": input_text, "day": int(day), "history": history},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            valid, validation_message = validate_result(result)
            if not valid:
                st.error(validation_message)
                st.stop()
            st.session_state.latest_ai_mode = response.headers.get("X-NeuroGuard-AI-Mode", "unknown")
            st.session_state.latest_llm_calls = response.headers.get("X-NeuroGuard-LLM-Calls", "unknown")
            st.session_state.latest = result
            st.session_state.timeline.append(
                {
                    "day": int(day),
                    "score": result["risk"]["score"],
                    "risk_level": result["risk"]["risk_level"],
                }
            )
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
    st.caption(
        "AI pipeline: "
        f"mode={st.session_state.get('latest_ai_mode', 'unknown')} · "
        f"LLM calls={st.session_state.get('latest_llm_calls', 'unknown')} · "
        "policy=max 1 call/request"
    )

    if len(st.session_state.timeline) >= 2:
        st.subheader("Recovery trend")
        first_score = st.session_state.timeline[0]["score"]
        latest_score = st.session_state.timeline[-1]["score"]
        if latest_score < first_score:
            st.caption(f"Trend: improving ({first_score} → {latest_score}). Continue progressing only while symptoms remain controlled.")
        elif latest_score > first_score:
            st.caption(f"Trend: worsening ({first_score} → {latest_score}). Pause progression and seek professional guidance.")
        else:
            st.caption(f"Trend: stable at {latest_score}. Continue monitoring symptoms and tolerance.")
        st.line_chart(
            [item["score"] for item in st.session_state.timeline],
            x_label="Check-in",
            y_label="Risk score",
        )
        st.table(st.session_state.timeline)
    elif st.session_state.timeline:
        st.subheader("Recovery trend")
        st.caption("One check-in recorded. Complete another daily check-in to see a recovery trend.")

    plan_left, plan_right = st.columns([1.5, 1])
    with plan_left:
        render_plan(result["plan"])
    with plan_right:
        st.subheader("Why this result?")
        st.write(result["explanation"])
        st.markdown("**Signals detected**")
        st.write(result["risk"].get("factors", "See the unified explanation and safety result."))

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
