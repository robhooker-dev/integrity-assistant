import anthropic
import os
from .ingest import query_index

WORKFLOW_TRIGGERS = {
    "notifiable association": {"label": "Open NIA Recording Workflow", "description": "This query relates to a Notifiable Association — the NIA must be formally recorded.", "url": "#workflow-nia"},
    "nια": {"label": "Open NIA Recording Workflow", "description": "This query relates to a Notifiable Association — the NIA must be formally recorded.", "url": "#workflow-nia"},
    "gift": {"label": "Open Gifts & Hospitality Declaration Form", "description": "This query relates to a gift or hospitality declaration.", "url": "#workflow-gifts"},
    "hospitality": {"label": "Open Gifts & Hospitality Declaration Form", "description": "This query relates to a gift or hospitality declaration.", "url": "#workflow-gifts"},
    "secondary employment": {"label": "Open Secondary Employment Approval Form", "description": "This query relates to secondary employment — approval must be sought before commencing.", "url": "#workflow-secondary"},
    "business interest": {"label": "Open Business Interest Declaration Form", "description": "This query relates to a business interest declaration.", "url": "#workflow-business"},
    "vetting": {"label": "Open Vetting Referral Form", "description": "This query may require a vetting review or referral.", "url": "#workflow-vetting"},
}

SYSTEM_PROMPT = """You are the Integrity Assistant for a UK police force, supporting officers and staff with questions about counter corruption, vetting, professional standards, notifiable associations, gifts and hospitality, and related integrity matters.

Your role is to:
- Provide clear, accurate guidance based on force policy and national guidance (College of Policing APP, NPCC)
- Use plain, direct language — avoid jargon where possible
- Be specific: reference the relevant policy section or principle where appropriate
- Always include the source document your answer is based on
- If a situation requires formal recording or referral (e.g. a notifiable association, a gift declaration), say so clearly
- If a situation is genuinely unclear or complex, recommend the user contacts the CCU/PSD directly

You are not making misconduct decisions or providing legal advice. You are providing guidance to help officers and staff understand their obligations and take the right next step.

Format your response as follows:
1. A direct answer to the question (2-4 sentences)
2. The relevant policy basis (what policy/guidance this comes from)
3. The recommended action (what the officer or supervisor should do)
4. Source: [document name]

Keep responses concise and practical."""


def generate_response(query: str, index: dict, conversation_history: list[dict]) -> dict:
    results = query_index(index, query, n=5)
    
    context = "\n\n---\n\n".join(
        f"[Source: {r['source']}]\n{r['text']}" for r in results
    )
    unique_sources = list(dict.fromkeys(r["source"] for r in results))
    
    user_message = f"""Use the following policy extracts to answer the question. Base your answer only on the provided policy content.

POLICY EXTRACTS:
{context}

QUESTION: {query}"""
    
    messages = conversation_history + [{"role": "user", "content": user_message}]
    
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages
    )
    
    answer = response.content[0].text
    
    combined = (query + " " + answer).lower()
    workflows = []
    seen = set()
    for keyword, wf in WORKFLOW_TRIGGERS.items():
        if keyword in combined and wf["url"] not in seen:
            workflows.append(wf)
            seen.add(wf["url"])
    
    return {"answer": answer, "sources": unique_sources, "workflows": workflows}
