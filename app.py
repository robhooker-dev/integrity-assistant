import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rag.ingest import get_index
from rag.chain import generate_response

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Integrity Assistant", page_icon="🛡️", layout="centered")

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1f3a 0%, #2d3561 100%);
        padding: 2rem; border-radius: 10px; margin-bottom: 1.5rem; text-align: center;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #a0b0d0; margin: 0.5rem 0 0 0; font-size: 0.9rem; }
    .disclaimer {
        background: #fff8e1; border-left: 4px solid #f9a825;
        padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1.5rem;
        font-size: 0.85rem; color: #555;
    }
    .source-tag {
        background: #e8f4fd; border: 1px solid #90caf9; color: #1565c0;
        padding: 2px 8px; border-radius: 12px; font-size: 0.78rem;
        margin-right: 4px; display: inline-block; margin-top: 4px;
    }
    .workflow-box {
        background: #e8f5e9; border: 1px solid #66bb6a; border-left: 4px solid #2e7d32;
        padding: 0.75rem 1rem; border-radius: 6px; margin-top: 0.75rem;
    }
    .workflow-box p { margin: 0; font-size: 0.88rem; color: #1b5e20; }
    .workflow-panel {
        background: #f8f9ff; border: 2px solid #3d52a0; border-radius: 10px;
        padding: 1.5rem; margin-top: 1.5rem;
    }
    .step-indicator {
        background: #3d52a0; color: white; padding: 0.3rem 0.8rem;
        border-radius: 20px; font-size: 0.8rem; display: inline-block; margin-bottom: 1rem;
    }
    .record-box {
        background: #1a1f3a; color: #e0e8ff; padding: 1.5rem;
        border-radius: 8px; font-family: monospace; font-size: 0.85rem;
        white-space: pre-wrap; margin-top: 1rem;
    }
    .chat-footer { font-size: 0.75rem; color: #999; text-align: center; margin-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛡️ Integrity Assistant</h1>
    <p>Counter Corruption · Vetting · Professional Standards · Notifiable Associations</p>
</div>
<div class="disclaimer">
    <strong>Guidance only.</strong> This assistant provides policy-based guidance to help you understand 
    your obligations and take the right next step. It does not make misconduct decisions or provide legal advice. 
    For complex matters, contact the CCU or PSD directly.
</div>
""", unsafe_allow_html=True)

# ── Index ───────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading policy documents...")
def load_index():
    return get_index()

index = load_index()

# ── Session state ───────────────────────────────────────────────────────────────
defaults = {
    "messages": [],
    "rag_history": [],
    "workflow": None,       # "nia" | "gifts" | None
    "workflow_step": 1,
    "workflow_data": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# NIA WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

def nia_workflow():
    step = st.session_state.workflow_step
    data = st.session_state.workflow_data

    st.markdown('<div class="workflow-panel">', unsafe_allow_html=True)
    st.markdown("### 📋 Notifiable Association — Recording Workflow")
    st.markdown(f'<span class="step-indicator">Step {step} of 5</span>', unsafe_allow_html=True)
    st.progress(step / 5)

    # ── Step 1: Officer details ────────────────────────────────────────────────
    if step == 1:
        st.markdown("**Officer / Staff Member Details**")
        st.caption("Details of the person who has, or may have, a notifiable association.")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full name", value=data.get("officer_name", ""))
            rank = st.selectbox("Rank / Grade", [
                "PC", "DC", "PS", "DS", "Inspector", "DI", "Chief Inspector",
                "Superintendent", "Police Staff — Grade A/B", "Police Staff — Grade C/D", "Other"
            ], index=["PC","DC","PS","DS","Inspector","DI","Chief Inspector",
                      "Superintendent","Police Staff — Grade A/B","Police Staff — Grade C/D","Other"]
                      .index(data.get("rank", "PC")))
        with col2:
            collar = st.text_input("Collar / payroll number", value=data.get("collar", ""))
            department = st.text_input("Department / team", value=data.get("department", ""))

        st.markdown("---")
        supervisor = st.text_input("Your name (supervising officer completing this record)", 
                                   value=data.get("supervisor", ""))

        if st.button("Next →", key="nia_s1", type="primary"):
            if not name or not collar or not supervisor:
                st.error("Please complete all required fields before continuing.")
            else:
                st.session_state.workflow_data.update({
                    "officer_name": name, "collar": collar,
                    "rank": rank, "department": department, "supervisor": supervisor
                })
                st.session_state.workflow_step = 2
                st.rerun()

    # ── Step 2: Nature of association ─────────────────────────────────────────
    elif step == 2:
        st.markdown("**Nature of the Association**")
        st.caption("Describe the association and the person involved.")
        
        relationship = st.selectbox("Relationship to officer", [
            "Immediate family member (parent, sibling, child)",
            "Partner / spouse",
            "Extended family member",
            "Close friend",
            "Acquaintance",
            "Former colleague",
            "Neighbour",
            "Other"
        ], index=["Immediate family member (parent, sibling, child)","Partner / spouse",
                  "Extended family member","Close friend","Acquaintance",
                  "Former colleague","Neighbour","Other"]
                  .index(data.get("relationship", "Close friend")))

        associate_desc = st.text_area(
            "Brief description of the associate (do not include full name if not necessary)",
            value=data.get("associate_desc", ""),
            placeholder="e.g. Male, approximately 35, lives in [area]"
        )
        known_how_long = st.selectbox("How long has this association existed?", [
            "Less than 1 year", "1–5 years", "5–10 years", "More than 10 years", "Unknown"
        ], index=["Less than 1 year","1–5 years","5–10 years",
                  "More than 10 years","Unknown"].index(data.get("known_how_long", "Unknown")))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="nia_s2_back"):
                st.session_state.workflow_step = 1
                st.rerun()
        with col2:
            if st.button("Next →", key="nia_s2", type="primary"):
                if not associate_desc:
                    st.error("Please provide a description of the associate.")
                else:
                    st.session_state.workflow_data.update({
                        "relationship": relationship,
                        "associate_desc": associate_desc,
                        "known_how_long": known_how_long
                    })
                    st.session_state.workflow_step = 3
                    st.rerun()

    # ── Step 3: Why it may be notifiable ──────────────────────────────────────
    elif step == 3:
        st.markdown("**Reason for Declaration**")
        st.caption("Select all criteria that apply. The association is notifiable if the associate falls into any of these categories.")

        reasons = st.multiselect(
            "The associate is known or suspected to be / have been:",
            options=[
                "Charged with a criminal offence — subject to current prosecution",
                "In possession of unspent criminal convictions",
                "Subject of a current police investigation",
                "Involved in serious organised crime",
                "Involved in drug supply or use",
                "Involved in domestic extremism or terrorism",
                "Dismissed from any police force or law enforcement agency",
                "Subject of counter-corruption intelligence",
                "A member of a group incompatible with the Standards of Professional Behaviour",
            ],
            default=data.get("reasons", [])
        )
        other_reason = st.text_area(
            "Any additional detail or other reason not listed above",
            value=data.get("other_reason", ""),
            placeholder="Optional"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="nia_s3_back"):
                st.session_state.workflow_step = 2
                st.rerun()
        with col2:
            if st.button("Next →", key="nia_s3", type="primary"):
                if not reasons and not other_reason:
                    st.error("Please select at least one reason why this association may be notifiable.")
                else:
                    st.session_state.workflow_data.update({
                        "reasons": reasons,
                        "other_reason": other_reason
                    })
                    st.session_state.workflow_step = 4
                    st.rerun()

    # ── Step 4: Circumstances and disclosure ──────────────────────────────────
    elif step == 4:
        st.markdown("**Circumstances of Disclosure**")

        how_aware = st.selectbox("How did you become aware of this association?", [
            "Officer / staff member self-declared",
            "Identified by supervisor during welfare / appraisal discussion",
            "Information received from a third party",
            "Intelligence received by CCU / PSD",
            "Identified during vetting review",
            "Other"
        ], index=["Officer / staff member self-declared",
                  "Identified by supervisor during welfare / appraisal discussion",
                  "Information received from a third party",
                  "Intelligence received by CCU / PSD",
                  "Identified during vetting review","Other"]
                  .index(data.get("how_aware", "Officer / staff member self-declared")))

        officer_told = st.radio(
            "Has the officer been informed that a formal declaration is required?",
            ["Yes", "No", "Not yet — pending CCU guidance"],
            index=["Yes","No","Not yet — pending CCU guidance"].index(data.get("officer_told", "Yes"))
        )

        live_ops_risk = st.radio(
            "Is there any known or suspected risk to live operations or intelligence?",
            ["No", "Yes — details below", "Unknown at this stage"],
            index=["No","Yes — details below","Unknown at this stage"]
            .index(data.get("live_ops_risk", "Unknown at this stage"))
        )

        ops_detail = ""
        if live_ops_risk == "Yes — details below":
            ops_detail = st.text_area("Briefly describe the operational risk",
                                      value=data.get("ops_detail", ""))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="nia_s4_back"):
                st.session_state.workflow_step = 3
                st.rerun()
        with col2:
            if st.button("Next →", key="nia_s4", type="primary"):
                st.session_state.workflow_data.update({
                    "how_aware": how_aware,
                    "officer_told": officer_told,
                    "live_ops_risk": live_ops_risk,
                    "ops_detail": ops_detail
                })
                st.session_state.workflow_step = 5
                st.rerun()

    # ── Step 5: Review and generate record ────────────────────────────────────
    elif step == 5:
        st.markdown("**Review and Generate Record**")
        st.caption("Check the details below before generating the NIA record.")

        d = st.session_state.workflow_data
        st.markdown(f"""
| Field | Detail |
|---|---|
| **Officer** | {d.get('officer_name')} ({d.get('rank')}) |
| **Collar / Payroll** | {d.get('collar')} |
| **Department** | {d.get('department', '—')} |
| **Completing supervisor** | {d.get('supervisor')} |
| **Relationship** | {d.get('relationship')} |
| **Known how long** | {d.get('known_how_long')} |
| **How aware** | {d.get('how_aware')} |
| **Officer informed** | {d.get('officer_told')} |
| **Operational risk** | {d.get('live_ops_risk')} |
        """)

        st.markdown("**Reasons for declaration:**")
        for r in d.get("reasons", []):
            st.markdown(f"- {r}")
        if d.get("other_reason"):
            st.markdown(f"- Other: {d.get('other_reason')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="nia_s5_back"):
                st.session_state.workflow_step = 4
                st.rerun()
        with col2:
            if st.button("✅ Generate NIA Record", key="nia_generate", type="primary"):
                st.session_state.workflow_step = 6
                st.rerun()

    # ── Step 6: Generated record ───────────────────────────────────────────────
    elif step == 6:
        d = st.session_state.workflow_data
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        reasons_text = "\n".join(f"  • {r}" for r in d.get("reasons", []))
        if d.get("other_reason"):
            reasons_text += f"\n  • Other: {d.get('other_reason')}"

        record = f"""NOTIFIABLE ASSOCIATION — INITIAL RECORD
════════════════════════════════════════════════════
Generated: {timestamp}
Status: PENDING CCU ASSESSMENT — refer immediately

SUBJECT OFFICER / STAFF MEMBER
  Name:            {d.get('officer_name')}
  Rank / Grade:    {d.get('rank')}
  Collar / Pay No: {d.get('collar')}
  Department:      {d.get('department', 'Not specified')}

COMPLETING SUPERVISOR
  Name:            {d.get('supervisor')}

ASSOCIATION DETAILS
  Relationship:    {d.get('relationship')}
  Duration:        {d.get('known_how_long')}
  Associate desc:  {d.get('associate_desc')}

REASON(S) FOR DECLARATION
{reasons_text}

CIRCUMSTANCES
  How identified:  {d.get('how_aware')}
  Officer informed of duty to declare: {d.get('officer_told')}

OPERATIONAL RISK ASSESSMENT
  Risk to live operations: {d.get('live_ops_risk')}
{('  Detail: ' + d.get('ops_detail')) if d.get('ops_detail') else ''}

NEXT STEPS (supervisor action required)
  1. Refer this record to the CCU/ACU without delay
  2. Do not share with the subject officer pending CCU assessment
  3. Do not restrict the officer's deployment without CCU authorisation
  4. Await CCU assessment outcome before taking further action
  5. Retain a copy of this record securely

════════════════════════════════════════════════════
THIS IS A DRAFT RECORD FOR CCU SUBMISSION
All NIA decisions are made solely by the CCU/ACU
════════════════════════════════════════════════════"""

        st.success("✅ NIA record generated. Copy this and forward to your CCU/ACU immediately.")
        st.markdown(f'<div class="record-box">{record}</div>', unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download record as .txt",
            data=record,
            file_name=f"NIA_record_{d.get('collar', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )

        st.markdown("---")
        if st.button("🔄 Start a new NIA record", use_container_width=True):
            st.session_state.workflow = None
            st.session_state.workflow_step = 1
            st.session_state.workflow_data = {}
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Cancel button (all steps except final)
    if st.session_state.workflow_step < 6:
        st.markdown("")
        if st.button("✕ Cancel workflow", key="cancel_wf"):
            st.session_state.workflow = None
            st.session_state.workflow_step = 1
            st.session_state.workflow_data = {}
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CHAT UI
# ══════════════════════════════════════════════════════════════════════════════

# Suggested questions (only when chat is empty and no workflow active)
if not st.session_state.messages and not st.session_state.workflow:
    st.markdown("**Example questions to get started:**")
    cols = st.columns(2)
    suggestions = [
        "One of my officers has a family member with recent drug convictions. Does this need to be declared?",
        "A local business offered our team Christmas hampers. Can we accept them?",
        "What are my responsibilities as a supervisor when I suspect an officer has an undeclared notifiable association?",
        "An officer wants to work weekend security shifts at a local venue. What needs to happen?",
    ]
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"sug_{i}", use_container_width=True):
            st.session_state["prefill"] = s
            st.rerun()

# Chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🛡️"):
        st.markdown(message["content"])

        if message["role"] == "assistant" and "sources" in message:
            if message["sources"]:
                source_html = "".join(
                    f'<span class="source-tag">📄 {s.replace("_"," ").replace(".txt","").replace(".pdf","")}</span>'
                    for s in message["sources"]
                )
                st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)

            if message.get("workflows"):
                for wf in message["workflows"]:
                    if wf["url"] == "#workflow-nia":
                        if st.button(f"📋 {wf['label']}", key=f"wf_{message['content'][:20]}"):
                            st.session_state.workflow = "nia"
                            st.session_state.workflow_step = 1
                            st.session_state.workflow_data = {}
                            st.rerun()
                    else:
                        st.markdown(f"""
                        <div class="workflow-box">
                            <p><strong>⚡ Action required:</strong> {wf['description']}</p>
                            <p style="margin-top:6px; color:#2e7d32; font-weight:600;">→ {wf['label']}
                            <span style="color:#888; font-size:0.78rem;"> (coming soon)</span></p>
                        </div>""", unsafe_allow_html=True)

# Active workflow panel
if st.session_state.workflow == "nia":
    nia_workflow()

# Chat input (hidden while workflow is active)
if not st.session_state.workflow:
    prefill = st.session_state.pop("prefill", None)
    prompt = st.chat_input("Ask about counter corruption, vetting, NIAs, gifts, business interests...") or prefill

    if prompt:
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner("Checking policy documents..."):
                result = generate_response(
                    query=prompt,
                    index=index,
                    conversation_history=st.session_state.rag_history
                )

            st.markdown(result["answer"])

            if result["sources"]:
                source_html = "".join(
                    f'<span class="source-tag">📄 {s.replace("_"," ").replace(".txt","").replace(".pdf","")}</span>'
                    for s in result["sources"]
                )
                st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)

            if result["workflows"]:
                for wf in result["workflows"]:
                    if wf["url"] == "#workflow-nia":
                        if st.button(f"📋 {wf['label']}", key=f"wf_new_{prompt[:15]}"):
                            st.session_state.workflow = "nia"
                            st.session_state.workflow_step = 1
                            st.session_state.workflow_data = {}
                            st.rerun()
                    else:
                        st.markdown(f"""
                        <div class="workflow-box">
                            <p><strong>⚡ Action required:</strong> {wf['description']}</p>
                            <p style="margin-top:6px; color:#2e7d32; font-weight:600;">→ {wf['label']}
                            <span style="color:#888; font-size:0.78rem;"> (coming soon)</span></p>
                        </div>""", unsafe_allow_html=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "workflows": result["workflows"]
        })
        st.session_state.rag_history.append({"role": "user", "content": prompt})
        st.session_state.rag_history.append({"role": "assistant", "content": result["answer"]})

# Footer
st.markdown("""
<div class="chat-footer">
    Integrity Assistant · Prototype v0.1 · Powered by Claude<br>
    Indexed: Notifiable Associations · Gifts & Hospitality · Counter Corruption APP · Business Interests
</div>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ Integrity Assistant")
    st.markdown("**Prototype v0.1**")
    st.divider()

    st.markdown("**Indexed policies**")
    docs_dir = Path(__file__).parent / "data" / "documents"
    for f in sorted(docs_dir.iterdir()):
        if f.suffix in [".txt", ".pdf"]:
            name = f.name.replace("_"," ").replace(".txt","").replace(".pdf","").title()
            st.markdown(f"📄 {name}")

    st.divider()
    st.markdown("**Workflows**")
    st.markdown("✅ NIA Recording")
    st.markdown("🔜 Gifts & Hospitality Declaration")
    st.markdown("🔜 Secondary Employment Approval")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.rag_history = []
        st.session_state.workflow = None
        st.session_state.workflow_step = 1
        st.session_state.workflow_data = {}
        st.rerun()

    st.divider()
    st.markdown("**Need human support?**")
    st.markdown("📞 Contact CCU/PSD directly for complex matters.")
    st.markdown("🔒 Use the force confidential reporting system for anonymous referrals.")
