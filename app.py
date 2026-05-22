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
    "messages": [], "rag_history": [],
    "workflow": None, "workflow_step": 1, "workflow_data": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Shared helpers ──────────────────────────────────────────────────────────────
RANKS = ["PC","DC","PS","DS","Inspector","DI","Chief Inspector",
         "Superintendent","Police Staff — Grade A/B","Police Staff — Grade C/D","Other"]

def officer_details_step(prefix):
    """Render officer + supervisor fields. Returns (valid, data_dict)."""
    d = st.session_state.workflow_data
    st.markdown("**Officer / Staff Member Details**")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full name", value=d.get("officer_name",""), key=f"{prefix}_name")
        rank = st.selectbox("Rank / Grade", RANKS,
                            index=RANKS.index(d.get("rank","PC")), key=f"{prefix}_rank")
    with col2:
        collar = st.text_input("Collar / payroll number", value=d.get("collar",""), key=f"{prefix}_collar")
        department = st.text_input("Department / team", value=d.get("department",""), key=f"{prefix}_dept")
    st.markdown("---")
    supervisor = st.text_input("Your name (supervising officer completing this record)",
                               value=d.get("supervisor",""), key=f"{prefix}_sup")
    return name, rank, collar, department, supervisor

def nav_buttons(step, prefix, total, valid_fn, save_fn):
    """Back / Next navigation."""
    col1, col2 = st.columns(2)
    with col1:
        if step > 1 and st.button("← Back", key=f"{prefix}_back_{step}"):
            st.session_state.workflow_step = step - 1
            st.rerun()
    with col2:
        label = "Next →" if step < total - 1 else "Review →"
        if st.button(label, key=f"{prefix}_next_{step}", type="primary"):
            if not valid_fn():
                st.error("Please complete all required fields before continuing.")
            else:
                save_fn()
                st.session_state.workflow_step = step + 1
                st.rerun()

def reset_workflow():
    st.session_state.workflow = None
    st.session_state.workflow_step = 1
    st.session_state.workflow_data = {}

def render_record(record, collar, prefix):
    st.success("✅ Record generated. Copy and forward to CCU/PSD immediately.")
    st.markdown(f'<div class="record-box">{record}</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download as .txt", data=record,
        file_name=f"{prefix}_record_{collar}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain", use_container_width=True)
    st.markdown("---")
    if st.button("🔄 Start a new record", use_container_width=True):
        reset_workflow()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 1 — NOTIFIABLE ASSOCIATION
# ══════════════════════════════════════════════════════════════════════════════
def nia_workflow():
    step = st.session_state.workflow_step
    d = st.session_state.workflow_data
    TOTAL = 6

    st.markdown('<div class="workflow-panel">', unsafe_allow_html=True)
    st.markdown("### 📋 Notifiable Association — Recording Workflow")
    st.markdown(f'<span class="step-indicator">Step {min(step,TOTAL-1)} of {TOTAL-1}</span>', unsafe_allow_html=True)
    st.progress(min(step / (TOTAL - 1), 1.0))

    if step == 1:
        name, rank, collar, department, supervisor = officer_details_step("nia1")
        def valid(): return bool(name and collar and supervisor)
        def save(): d.update({"officer_name":name,"rank":rank,"collar":collar,"department":department,"supervisor":supervisor})
        nav_buttons(step, "nia", TOTAL, valid, save)

    elif step == 2:
        st.markdown("**Nature of the Association**")
        RELS = ["Immediate family member","Partner / spouse","Extended family member",
                "Close friend","Acquaintance","Former colleague","Neighbour","Other"]
        DURS = ["Less than 1 year","1–5 years","5–10 years","More than 10 years","Unknown"]
        relationship = st.selectbox("Relationship to officer", RELS,
                                    index=RELS.index(d.get("relationship","Close friend")))
        associate_desc = st.text_area("Brief description of the associate",
                                      value=d.get("associate_desc",""),
                                      placeholder="e.g. Male, approximately 35, lives in [area]")
        known_how_long = st.selectbox("How long has this association existed?", DURS,
                                      index=DURS.index(d.get("known_how_long","Unknown")))
        def valid(): return bool(associate_desc)
        def save(): d.update({"relationship":relationship,"associate_desc":associate_desc,"known_how_long":known_how_long})
        nav_buttons(step, "nia", TOTAL, valid, save)

    elif step == 3:
        st.markdown("**Reason for Declaration**")
        st.caption("Select all criteria that apply.")
        OPTS = [
            "Charged with a criminal offence — subject to current prosecution",
            "In possession of unspent criminal convictions",
            "Subject of a current police investigation",
            "Involved in serious organised crime",
            "Involved in drug supply or use",
            "Involved in domestic extremism or terrorism",
            "Dismissed from any police force or law enforcement agency",
            "Subject of counter-corruption intelligence",
            "Member of a group incompatible with the Standards of Professional Behaviour",
        ]
        reasons = st.multiselect("The associate is known or suspected to:", OPTS, default=d.get("reasons",[]))
        other_reason = st.text_area("Other reason / additional detail", value=d.get("other_reason",""), placeholder="Optional")
        def valid(): return bool(reasons or other_reason)
        def save(): d.update({"reasons":reasons,"other_reason":other_reason})
        nav_buttons(step, "nia", TOTAL, valid, save)

    elif step == 4:
        st.markdown("**Circumstances of Disclosure**")
        HOWS = ["Officer / staff member self-declared",
                "Identified by supervisor during welfare / appraisal",
                "Information received from a third party",
                "Intelligence received by CCU / PSD",
                "Identified during vetting review","Other"]
        TOLD = ["Yes","No","Not yet — pending CCU guidance"]
        RISK = ["No","Yes — details below","Unknown at this stage"]
        how_aware = st.selectbox("How did you become aware?", HOWS, index=HOWS.index(d.get("how_aware",HOWS[0])))
        officer_told = st.radio("Has the officer been told a formal declaration is required?", TOLD,
                                index=TOLD.index(d.get("officer_told","Yes")))
        live_ops_risk = st.radio("Is there any known risk to live operations or intelligence?", RISK,
                                 index=RISK.index(d.get("live_ops_risk","Unknown at this stage")))
        ops_detail = ""
        if live_ops_risk == "Yes — details below":
            ops_detail = st.text_area("Describe the operational risk", value=d.get("ops_detail",""))
        def valid(): return True
        def save(): d.update({"how_aware":how_aware,"officer_told":officer_told,"live_ops_risk":live_ops_risk,"ops_detail":ops_detail})
        nav_buttons(step, "nia", TOTAL, valid, save)

    elif step == 5:
        st.markdown("**Review before generating record**")
        st.markdown(f"""
| Field | Detail |
|---|---|
| **Officer** | {d.get('officer_name')} ({d.get('rank')}) |
| **Collar / Pay No** | {d.get('collar')} |
| **Department** | {d.get('department','—')} |
| **Supervisor** | {d.get('supervisor')} |
| **Relationship** | {d.get('relationship')} |
| **Known how long** | {d.get('known_how_long')} |
| **How identified** | {d.get('how_aware')} |
| **Officer informed** | {d.get('officer_told')} |
| **Operational risk** | {d.get('live_ops_risk')} |
        """)
        st.markdown("**Reasons:**")
        for r in d.get("reasons",[]): st.markdown(f"- {r}")
        if d.get("other_reason"): st.markdown(f"- Other: {d.get('other_reason')}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="nia_rev_back"):
                st.session_state.workflow_step = 4; st.rerun()
        with col2:
            if st.button("✅ Generate NIA Record", type="primary", key="nia_gen"):
                st.session_state.workflow_step = 6; st.rerun()

    elif step == 6:
        reasons_text = "\n".join(f"  • {r}" for r in d.get("reasons",[]))
        if d.get("other_reason"): reasons_text += f"\n  • Other: {d.get('other_reason')}"
        record = f"""NOTIFIABLE ASSOCIATION — INITIAL RECORD
{'═'*52}
Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Status:    PENDING CCU ASSESSMENT — refer immediately

SUBJECT OFFICER / STAFF MEMBER
  Name:            {d.get('officer_name')}
  Rank / Grade:    {d.get('rank')}
  Collar / Pay No: {d.get('collar')}
  Department:      {d.get('department','Not specified')}

COMPLETING SUPERVISOR
  Name:            {d.get('supervisor')}

ASSOCIATION DETAILS
  Relationship:    {d.get('relationship')}
  Duration:        {d.get('known_how_long')}
  Associate:       {d.get('associate_desc')}

REASON(S) FOR DECLARATION
{reasons_text}

CIRCUMSTANCES
  How identified:  {d.get('how_aware')}
  Officer informed of duty to declare: {d.get('officer_told')}

OPERATIONAL RISK
  Risk to live operations: {d.get('live_ops_risk')}
{('  Detail: ' + d.get('ops_detail','')) if d.get('ops_detail') else ''}
NEXT STEPS
  1. Refer to CCU/ACU without delay
  2. Do not share with subject officer pending CCU assessment
  3. Do not restrict deployment without CCU authorisation
  4. Await CCU outcome before taking further action
  5. Retain a copy of this record securely

{'═'*52}
DRAFT RECORD FOR CCU SUBMISSION ONLY
All NIA decisions are made solely by the CCU/ACU
{'═'*52}"""
        render_record(record, d.get('collar','unknown'), "NIA")

    st.markdown('</div>', unsafe_allow_html=True)
    if step < 6:
        if st.button("✕ Cancel", key="nia_cancel"):
            reset_workflow(); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 2 — GIFTS & HOSPITALITY
# ══════════════════════════════════════════════════════════════════════════════
def gifts_workflow():
    step = st.session_state.workflow_step
    d = st.session_state.workflow_data
    TOTAL = 6

    st.markdown('<div class="workflow-panel">', unsafe_allow_html=True)
    st.markdown("### 🎁 Gifts & Hospitality — Declaration Workflow")
    st.markdown(f'<span class="step-indicator">Step {min(step,TOTAL-1)} of {TOTAL-1}</span>', unsafe_allow_html=True)
    st.progress(min(step / (TOTAL - 1), 1.0))

    if step == 1:
        name, rank, collar, department, supervisor = officer_details_step("gh1")
        def valid(): return bool(name and collar and supervisor)
        def save(): d.update({"officer_name":name,"rank":rank,"collar":collar,"department":department,"supervisor":supervisor})
        nav_buttons(step, "gh", TOTAL, valid, save)

    elif step == 2:
        st.markdown("**Nature of the Gift or Hospitality**")
        TYPES = ["Gift (physical item or voucher)","Cash or cash equivalent",
                 "Hospitality (food, drink, entertainment)","Accommodation or travel",
                 "Event tickets","Discount or service provided free of charge","Other"]
        gift_type = st.selectbox("Type of offer", TYPES, index=TYPES.index(d.get("gift_type",TYPES[0])))
        description = st.text_area("Description of the gift or hospitality",
                                   value=d.get("description",""),
                                   placeholder="e.g. Bottle of whisky, estimated value £30")
        col1, col2 = st.columns(2)
        with col1:
            value_est = st.text_input("Estimated value (£)", value=d.get("value_est",""),
                                     placeholder="e.g. 25")
        with col2:
            offered_by = st.text_input("Offered by (person / organisation)",
                                       value=d.get("offered_by",""))
        date_offered = st.date_input("Date offered", value=d.get("date_offered", datetime.today()))
        def valid(): return bool(description and offered_by)
        def save(): d.update({"gift_type":gift_type,"description":description,"value_est":value_est,
                               "offered_by":offered_by,"date_offered":str(date_offered)})
        nav_buttons(step, "gh", TOTAL, valid, save)

    elif step == 3:
        st.markdown("**Circumstances of the Offer**")
        CONTEXTS = ["In connection with police duties","During a community / partnership event",
                    "Seasonal / goodwill gesture","Personal / social context","Unknown / unclear"]
        context = st.selectbox("Context of the offer", CONTEXTS, index=CONTEXTS.index(d.get("context",CONTEXTS[0])))
        OUTCOMES = ["Refused","Accepted","Partially accepted (e.g. shared with team)","Not yet decided"]
        outcome = st.radio("Was it accepted or refused?", OUTCOMES,
                           index=OUTCOMES.index(d.get("outcome","Refused")))
        offerer_status = st.multiselect("Does the person / organisation offering this:",
            options=["Have an ongoing business relationship with the force",
                     "Have a pending tender or contract with the force",
                     "Have a previous relationship with the force",
                     "Have a criminal record or be subject to investigation",
                     "None of the above"],
            default=d.get("offerer_status",["None of the above"]))
        def valid(): return True
        def save(): d.update({"context":context,"outcome":outcome,"offerer_status":offerer_status})
        nav_buttons(step, "gh", TOTAL, valid, save)

    elif step == 4:
        st.markdown("**Reason for Declaration**")
        st.caption("Confirm which threshold(s) this offer meets.")
        REASONS = ["Estimated value exceeds £10",
                   "Cash or cash equivalent — must always be declared and refused",
                   "Repeated offers from the same source",
                   "Offered by a person or organisation with a business interest in the force",
                   "Offered by a person under investigation",
                   "Offered in circumstances suggesting an attempt to influence a policing decision",
                   "Uncertain whether it should be accepted — declaring as a precaution"]
        dec_reasons = st.multiselect("Reason(s) for declaring", REASONS, default=d.get("dec_reasons",[]))
        additional = st.text_area("Any additional context", value=d.get("additional",""), placeholder="Optional")
        def valid(): return bool(dec_reasons)
        def save(): d.update({"dec_reasons":dec_reasons,"additional":additional})
        nav_buttons(step, "gh", TOTAL, valid, save)

    elif step == 5:
        st.markdown("**Review before generating declaration**")
        st.markdown(f"""
| Field | Detail |
|---|---|
| **Officer** | {d.get('officer_name')} ({d.get('rank')}) |
| **Collar / Pay No** | {d.get('collar')} |
| **Department** | {d.get('department','—')} |
| **Supervisor** | {d.get('supervisor')} |
| **Type** | {d.get('gift_type')} |
| **Description** | {d.get('description')} |
| **Estimated value** | £{d.get('value_est','Not specified')} |
| **Offered by** | {d.get('offered_by')} |
| **Date offered** | {d.get('date_offered')} |
| **Context** | {d.get('context')} |
| **Outcome** | {d.get('outcome')} |
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="gh_rev_back"):
                st.session_state.workflow_step = 4; st.rerun()
        with col2:
            if st.button("✅ Generate Declaration", type="primary", key="gh_gen"):
                st.session_state.workflow_step = 6; st.rerun()

    elif step == 6:
        d = st.session_state.workflow_data
        reasons_text = "\n".join(f"  • {r}" for r in d.get("dec_reasons",[]))
        offerer_text = "\n".join(f"  • {r}" for r in d.get("offerer_status",[]))

        # Auto-flag cash offers
        flag = ""
        if "Cash" in d.get("gift_type","") or "cash" in d.get("gift_type",""):
            flag = "\n  ⚠ CASH OFFER — must be refused regardless of value. Refer to PSD immediately."

        record = f"""GIFTS & HOSPITALITY — DECLARATION RECORD
{'═'*52}
Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Status:    FOR LINE MANAGER REVIEW AND REGISTER ENTRY

OFFICER / STAFF MEMBER
  Name:            {d.get('officer_name')}
  Rank / Grade:    {d.get('rank')}
  Collar / Pay No: {d.get('collar')}
  Department:      {d.get('department','Not specified')}

COMPLETING SUPERVISOR
  Name:            {d.get('supervisor')}

OFFER DETAILS
  Type:            {d.get('gift_type')}
  Description:     {d.get('description')}
  Estimated value: £{d.get('value_est','Not specified')}
  Offered by:      {d.get('offered_by')}
  Date offered:    {d.get('date_offered')}
  Context:         {d.get('context')}
  Outcome:         {d.get('outcome')}

OFFERER STATUS
{offerer_text}

REASON(S) FOR DECLARATION
{reasons_text}
{flag}
ADDITIONAL CONTEXT
  {d.get('additional','None') or 'None'}

NEXT STEPS
  1. Record on the force Gifts & Hospitality Register within 5 working days
  2. Line manager to determine whether offer was appropriately handled
  3. Refer to PSD if offer value, context, or offerer status is unclear
  4. Retain a copy of this declaration securely

{'═'*52}
DRAFT DECLARATION — FOR LINE MANAGER AND REGISTER USE
{'═'*52}"""
        render_record(record, d.get('collar','unknown'), "GH")

    st.markdown('</div>', unsafe_allow_html=True)
    if step < 6:
        if st.button("✕ Cancel", key="gh_cancel"):
            reset_workflow(); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 3 — BUSINESS INTERESTS
# ══════════════════════════════════════════════════════════════════════════════
def business_workflow():
    step = st.session_state.workflow_step
    d = st.session_state.workflow_data
    TOTAL = 6

    st.markdown('<div class="workflow-panel">', unsafe_allow_html=True)
    st.markdown("### 💼 Business Interests — Declaration Workflow")
    st.markdown(f'<span class="step-indicator">Step {min(step,TOTAL-1)} of {TOTAL-1}</span>', unsafe_allow_html=True)
    st.progress(min(step / (TOTAL - 1), 1.0))

    if step == 1:
        name, rank, collar, department, supervisor = officer_details_step("bi1")
        def valid(): return bool(name and collar and supervisor)
        def save(): d.update({"officer_name":name,"rank":rank,"collar":collar,"department":department,"supervisor":supervisor})
        nav_buttons(step, "bi", TOTAL, valid, save)

    elif step == 2:
        st.markdown("**Nature of the Business Interest**")
        TYPES = ["Additional employment (paid)","Additional employment (unpaid / voluntary)",
                 "Self-employment / sole trader","Directorship or partnership",
                 "Shareholding or financial interest in a business",
                 "Land or property used for commercial purposes","Other"]
        interest_type = st.selectbox("Type of business interest", TYPES,
                                     index=TYPES.index(d.get("interest_type",TYPES[0])))
        business_name = st.text_input("Name of employer / business / organisation",
                                      value=d.get("business_name",""))
        nature = st.text_area("Brief description of the role or interest",
                              value=d.get("nature",""),
                              placeholder="e.g. Weekend bar work at local pub, approx 8hrs per week")
        col1, col2 = st.columns(2)
        with col1:
            hours = st.text_input("Hours per week (if applicable)", value=d.get("hours",""),
                                  placeholder="e.g. 8")
        with col2:
            paid = st.radio("Paid or unpaid?", ["Paid","Unpaid","Mixed"],
                            index=["Paid","Unpaid","Mixed"].index(d.get("paid","Paid")))
        def valid(): return bool(business_name and nature)
        def save(): d.update({"interest_type":interest_type,"business_name":business_name,
                               "nature":nature,"hours":hours,"paid":paid})
        nav_buttons(step, "bi", TOTAL, valid, save)

    elif step == 3:
        st.markdown("**Conflict of Interest Assessment**")
        st.caption("Answer honestly — this helps the CCU/PSD assess whether approval can be granted.")

        conflicts = st.multiselect("Does this interest involve any of the following?",
            options=[
                "Use of police skills, powers, or knowledge in a private capacity",
                "Work for a person or organisation known to be involved in criminal activity",
                "A financial relationship with a person currently under police investigation",
                "Work in the private security or investigation sector",
                "Work at or interest in licensed premises",
                "Work as a legal representative in cases involving the force",
                "Work that could impair ability to perform police duties",
                "Work that could bring the force into disrepute",
                "None of the above",
            ],
            default=d.get("conflicts",["None of the above"]))

        commenced = st.radio("Has this interest already commenced?",
                             ["No — seeking approval before starting",
                              "Yes — recently commenced, declaring retrospectively",
                              "Yes — existing declared interest, notifying a change"],
                             index=["No — seeking approval before starting",
                                    "Yes — recently commenced, declaring retrospectively",
                                    "Yes — existing declared interest, notifying a change"]
                             .index(d.get("commenced","No — seeking approval before starting")))

        def valid(): return bool(conflicts)
        def save(): d.update({"conflicts":conflicts,"commenced":commenced})
        nav_buttons(step, "bi", TOTAL, valid, save)

    elif step == 4:
        st.markdown("**Household Members**")
        st.caption("Business interests held by household members must also be declared where they could create a conflict.")

        household_interest = st.radio(
            "Does any household member have a business interest that may be relevant?",
            ["No","Yes — details below","Unknown / not sure"],
            index=["No","Yes — details below","Unknown / not sure"]
            .index(d.get("household_interest","No")))

        household_detail = ""
        if household_interest == "Yes — details below":
            household_detail = st.text_area("Brief details of household member's interest",
                                            value=d.get("household_detail",""))

        additional = st.text_area("Any other relevant information",
                                  value=d.get("bi_additional",""), placeholder="Optional")

        def valid(): return True
        def save(): d.update({"household_interest":household_interest,
                               "household_detail":household_detail,"bi_additional":additional})
        nav_buttons(step, "bi", TOTAL, valid, save)

    elif step == 5:
        st.markdown("**Review before generating declaration**")
        st.markdown(f"""
| Field | Detail |
|---|---|
| **Officer** | {d.get('officer_name')} ({d.get('rank')}) |
| **Collar / Pay No** | {d.get('collar')} |
| **Department** | {d.get('department','—')} |
| **Supervisor** | {d.get('supervisor')} |
| **Type of interest** | {d.get('interest_type')} |
| **Business / employer** | {d.get('business_name')} |
| **Hours per week** | {d.get('hours','—')} |
| **Paid / unpaid** | {d.get('paid')} |
| **Commenced** | {d.get('commenced')} |
| **Household member interest** | {d.get('household_interest')} |
        """)
        if d.get("conflicts"):
            st.markdown("**Potential conflicts identified:**")
            for c in d.get("conflicts",[]): st.markdown(f"- {c}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="bi_rev_back"):
                st.session_state.workflow_step = 4; st.rerun()
        with col2:
            if st.button("✅ Generate Declaration", type="primary", key="bi_gen"):
                st.session_state.workflow_step = 6; st.rerun()

    elif step == 6:
        d = st.session_state.workflow_data
        conflicts = d.get("conflicts",[])
        conflict_text = "\n".join(f"  • {c}" for c in conflicts)

        # Simple flag logic
        high_risk = [c for c in conflicts if any(x in c for x in
            ["criminal activity","investigation","security","legal representative","disrepute"])]
        if high_risk:
            flag = "\n  ⚠ HIGH RISK FLAGS IDENTIFIED — approval unlikely without further assessment."
            recommendation = "REFER TO PSD/CCU FOR ASSESSMENT — conflicts identified that may prevent approval"
        elif "None of the above" in conflicts or not conflicts:
            flag = ""
            recommendation = "FORWARD TO LINE MANAGER — no obvious conflicts identified, approval may be granted"
        else:
            flag = "\n  ℹ Conflicts identified — refer to PSD for assessment before approval."
            recommendation = "REFER TO PSD FOR ASSESSMENT — further review required"

        record = f"""BUSINESS INTERESTS — DECLARATION RECORD
{'═'*52}
Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Status:    {recommendation}

OFFICER / STAFF MEMBER
  Name:            {d.get('officer_name')}
  Rank / Grade:    {d.get('rank')}
  Collar / Pay No: {d.get('collar')}
  Department:      {d.get('department','Not specified')}

COMPLETING SUPERVISOR
  Name:            {d.get('supervisor')}

BUSINESS INTEREST DETAILS
  Type:            {d.get('interest_type')}
  Business / org:  {d.get('business_name')}
  Description:     {d.get('nature')}
  Hours per week:  {d.get('hours','Not specified')}
  Paid / unpaid:   {d.get('paid')}
  Status:          {d.get('commenced')}

CONFLICT OF INTEREST ASSESSMENT
{conflict_text or '  • None identified'}
{flag}
HOUSEHOLD MEMBERS
  Household member interest: {d.get('household_interest')}
{('  Detail: ' + d.get('household_detail','')) if d.get('household_detail') else ''}
ADDITIONAL INFORMATION
  {d.get('bi_additional','None') or 'None'}

NEXT STEPS
  1. Forward to line manager for initial review
  2. Line manager refers to PSD if conflicts are identified
  3. Officer must not commence the interest until approved
  4. If already commenced, officer should be advised to suspend pending approval
  5. Retain a copy of this declaration securely

{'═'*52}
DRAFT DECLARATION — APPROVAL REQUIRED BEFORE COMMENCING
All approvals are granted by PSD / line management chain
{'═'*52}"""
        render_record(record, d.get('collar','unknown'), "BI")

    st.markdown('</div>', unsafe_allow_html=True)
    if step < 6:
        if st.button("✕ Cancel", key="bi_cancel"):
            reset_workflow(); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW BUTTON RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def render_workflow_buttons(workflows, key_prefix):
    for wf in workflows:
        if wf["url"] == "#workflow-nia":
            if st.button(f"📋 {wf['label']}", key=f"wf_nia_{key_prefix}"):
                st.session_state.workflow = "nia"
                st.session_state.workflow_step = 1
                st.session_state.workflow_data = {}
                st.rerun()
        elif wf["url"] == "#workflow-gifts":
            if st.button(f"🎁 {wf['label']}", key=f"wf_gh_{key_prefix}"):
                st.session_state.workflow = "gifts"
                st.session_state.workflow_step = 1
                st.session_state.workflow_data = {}
                st.rerun()
        elif wf["url"] == "#workflow-business":
            if st.button(f"💼 {wf['label']}", key=f"wf_bi_{key_prefix}"):
                st.session_state.workflow = "business"
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


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CHAT UI
# ══════════════════════════════════════════════════════════════════════════════
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

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🛡️"):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            if message["sources"]:
                source_html = "".join(
                    f'<span class="source-tag">📄 {s.replace("_"," ").replace(".txt","").replace(".pdf","")}</span>'
                    for s in message["sources"])
                st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)
            if message.get("workflows"):
                render_workflow_buttons(message["workflows"], message["content"][:15])

# Active workflow
if st.session_state.workflow == "nia":
    nia_workflow()
elif st.session_state.workflow == "gifts":
    gifts_workflow()
elif st.session_state.workflow == "business":
    business_workflow()

# Chat input
if not st.session_state.workflow:
    prefill = st.session_state.pop("prefill", None)
    prompt = st.chat_input("Ask about counter corruption, vetting, NIAs, gifts, business interests...") or prefill

    if prompt:
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner("Checking policy documents..."):
                result = generate_response(query=prompt, index=index,
                                           conversation_history=st.session_state.rag_history)
            st.markdown(result["answer"])
            if result["sources"]:
                source_html = "".join(
                    f'<span class="source-tag">📄 {s.replace("_"," ").replace(".txt","").replace(".pdf","")}</span>'
                    for s in result["sources"])
                st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)
            if result["workflows"]:
                render_workflow_buttons(result["workflows"], prompt[:15])

        st.session_state.messages.append({"role": "assistant", "content": result["answer"],
                                           "sources": result["sources"], "workflows": result["workflows"]})
        st.session_state.rag_history.append({"role": "user", "content": prompt})
        st.session_state.rag_history.append({"role": "assistant", "content": result["answer"]})

st.markdown("""
<div class="chat-footer">
    Integrity Assistant · Prototype v0.1 · Powered by Claude<br>
    Indexed: Notifiable Associations · Gifts & Hospitality · Counter Corruption APP · Business Interests
</div>""", unsafe_allow_html=True)

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
    st.markdown("✅ Gifts & Hospitality Declaration")
    st.markdown("✅ Business Interests Declaration")
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v if not isinstance(v, (list, dict)) else type(v)()
        st.rerun()
    st.divider()
    st.markdown("**Need human support?**")
    st.markdown("📞 Contact CCU/PSD directly for complex matters.")
    st.markdown("🔒 Use the force confidential reporting system for anonymous referrals.")
