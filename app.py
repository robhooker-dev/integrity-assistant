import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rag.ingest import get_index
from rag.chain import generate_response

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Integrity Assistant",
    page_icon="🛡️",
    layout="centered"
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1f3a 0%, #2d3561 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #a0b0d0; margin: 0.5rem 0 0 0; font-size: 0.9rem; }

    .disclaimer {
        background: #fff8e1;
        border-left: 4px solid #f9a825;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-bottom: 1.5rem;
        font-size: 0.85rem;
        color: #555;
    }

    .source-tag {
        background: #e8f4fd;
        border: 1px solid #90caf9;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        margin-right: 4px;
        display: inline-block;
        margin-top: 4px;
    }

    .workflow-box {
        background: #e8f5e9;
        border: 1px solid #66bb6a;
        border-left: 4px solid #2e7d32;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin-top: 0.75rem;
    }
    .workflow-box p { margin: 0; font-size: 0.88rem; color: #1b5e20; }
    .workflow-box strong { color: #1b5e20; }

    .chat-footer {
        font-size: 0.75rem;
        color: #999;
        text-align: center;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛡️ Integrity Assistant</h1>
    <p>Counter Corruption · Vetting · Professional Standards · Notifiable Associations</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
    <strong>Guidance only.</strong> This assistant provides policy-based guidance to help you understand your obligations 
    and take the right next step. It does not make misconduct decisions or provide legal advice. 
    For complex matters, contact the CCU or PSD directly.
</div>
""", unsafe_allow_html=True)

# ── Vector store (cached so it only loads once) ─────────────────────────────────
@st.cache_resource(show_spinner="Loading policy documents...")
def load_vector_store():
    return get_index()

index = load_vector_store()

# ── Session state ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_history" not in st.session_state:
    st.session_state.rag_history = []  # clean history for Claude API

# ── Suggested questions ─────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("**Example questions to get started:**")
    cols = st.columns(2)
    suggestions = [
        "One of my officers has a family member with recent drug convictions. Does this need to be declared?",
        "A local business offered our team Christmas hampers. Can we accept them?",
        "What are my responsibilities as a supervisor when I suspect an officer has an undeclared notifiable association?",
        "An officer wants to work weekend security shifts at a local venue. What needs to happen?",
    ]
    for i, suggestion in enumerate(suggestions):
        col = cols[i % 2]
        if col.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
            st.session_state["prefill"] = suggestion
            st.rerun()

# ── Display chat history ────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🛡️"):
        st.markdown(message["content"])
        
        # Show sources and workflows for assistant messages
        if message["role"] == "assistant" and "sources" in message:
            if message["sources"]:
                source_html = "".join(
                    f'<span class="source-tag">📄 {s.replace("_", " ").replace(".txt", "").replace(".pdf", "")}</span>'
                    for s in message["sources"]
                )
                st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)
            
            if message.get("workflows"):
                for wf in message["workflows"]:
                    st.markdown(f"""
                    <div class="workflow-box">
                        <p><strong>⚡ Action required:</strong> {wf['description']}</p>
                        <p style="margin-top:6px;">
                            <a href="{wf['url']}" style="color:#2e7d32; font-weight:600;">→ {wf['label']}</a>
                            <span style="color:#888; font-size:0.78rem;"> (workflow integration coming)</span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

# ── Chat input ──────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("prefill", None)
prompt = st.chat_input("Ask about counter corruption, vetting, NIAs, gifts, business interests...") or prefill

if prompt:
    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate response
    with st.chat_message("assistant", avatar="🛡️"):
        with st.spinner("Checking policy documents..."):
            result = generate_response(
                query=prompt,
                index=index,
                conversation_history=st.session_state.rag_history
            )
        
        st.markdown(result["answer"])
        
        # Sources
        if result["sources"]:
            source_html = "".join(
                f'<span class="source-tag">📄 {s.replace("_", " ").replace(".txt", "").replace(".pdf", "")}</span>'
                for s in result["sources"]
            )
            st.markdown(f"**Sources:** {source_html}", unsafe_allow_html=True)
        
        # Workflow triggers
        if result["workflows"]:
            for wf in result["workflows"]:
                st.markdown(f"""
                <div class="workflow-box">
                    <p><strong>⚡ Action required:</strong> {wf['description']}</p>
                    <p style="margin-top:6px;">
                        <a href="{wf['url']}" style="color:#2e7d32; font-weight:600;">→ {wf['label']}</a>
                        <span style="color:#888; font-size:0.78rem;"> (workflow integration coming)</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    # Update histories
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "workflows": result["workflows"]
    })
    
    # Update RAG history (clean version for Claude API — no context injection)
    st.session_state.rag_history.append({"role": "user", "content": prompt})
    st.session_state.rag_history.append({"role": "assistant", "content": result["answer"]})

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="chat-footer">
    Integrity Assistant · Prototype v0.1 · Powered by Claude + ChromaDB<br>
    Policy documents indexed: Notifiable Associations · Gifts & Hospitality · Counter Corruption APP · Business Interests
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
            name = f.name.replace("_", " ").replace(".txt", "").replace(".pdf", "").title()
            st.markdown(f"📄 {name}")
    
    st.divider()
    
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.rag_history = []
        st.rerun()
    
    st.divider()
    st.markdown("**Need human support?**")
    st.markdown("📞 Contact CCU/PSD directly for complex or sensitive matters.")
    st.markdown("🔒 Use the force confidential reporting system for anonymous referrals.")
