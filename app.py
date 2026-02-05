import streamlit as st
import pdfplumber
import requests
import json
import re

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="AI-Powered Document Orchestrator",
    layout="wide"
)

st.title("📄 AI-Powered Document Orchestrator")
st.write(
    "Upload a document, ask an analytical question, extract structured insights using AI, "
    "and optionally trigger a conditional alert email."
)

st.divider()

# -----------------------------
# STAGE 1: Upload & Question
# -----------------------------
st.header("1️⃣ Upload Document & Ask a Question")

uploaded_file = st.file_uploader(
    "Upload a document (PDF or TXT)",
    type=["pdf", "txt"]
)

user_question = st.text_input(
    "Enter your analytical question about the document"
)

analyze_clicked = st.button("Analyze Document")

# -----------------------------
# JSON EXTRACTION (SAFE)
# -----------------------------
def extract_json_from_text(text: str):
    if not text or not text.strip():
        raise ValueError("Empty AI response")

    text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON detected")

    return json.loads(text[start:end + 1])

# -----------------------------
# AI ANALYSIS FUNCTION
# -----------------------------
def analyze_with_ai(document_text, user_question):
    api_key = st.secrets["OPENROUTER_API_KEY"]

    def call_ai(messages):
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": messages,
                "temperature": 0,
                "max_tokens": 600,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )

        if response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()["choices"][0]["message"].get("content", "")

    prompt = [
        {
            "role": "system",
            "content": "You MUST return ONLY valid JSON. No explanations."
        },
        {
            "role": "user",
            "content": f"""
Return JSON in EXACTLY this format:
{{
  "key_points": ["point 1", "point 2"],
  "risk_level": "Low | Medium | High",
  "risk_reason": "string",
  "summary": "string"
}}

User Question:
{user_question}

Document Text:
{document_text[:6000]}
"""
        }
    ]

    # Attempt 1
    try:
        return extract_json_from_text(call_ai(prompt))
    except Exception:
        pass

    # Attempt 2 (repair)
    try:
        repair_prompt = [
            {"role": "system", "content": "Fix and return ONLY valid JSON."},
            {"role": "user", "content": call_ai(prompt)}
        ]
        return extract_json_from_text(call_ai(repair_prompt))
    except Exception:
        pass

    # Attempt 3 (final retry)
    return extract_json_from_text(call_ai(prompt))

# -----------------------------
# STAGE 2: Document Analysis
# -----------------------------
if analyze_clicked:
    st.divider()
    st.header("2️⃣ Document Analysis")

    if not uploaded_file:
        st.error("Please upload a document.")
        st.stop()

    if uploaded_file.type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            extracted_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    else:
        extracted_text = uploaded_file.read().decode("utf-8")

    st.subheader("📄 Extracted Text Preview")
    st.text_area("Content", extracted_text[:3000], height=300)

    with st.spinner("Analyzing document with AI..."):
        try:
            structured_data = analyze_with_ai(
                extracted_text,
                user_question
            )

            st.subheader("🧩 Structured Insights")
            st.json(structured_data)

            st.session_state.update({
                "analysis_done": True,
                "structured_data": structured_data,
                "extracted_text": extracted_text,
                "user_question": user_question
            })

        except Exception:
            st.error("AI analysis failed. Please try again.")
            st.stop()

# -----------------------------
## -----------------------------
# STAGE 3: Email Trigger
# -----------------------------
if st.session_state.get("analysis_done"):

    st.divider()
    st.header("3️⃣ Send Conditional Alert Email")

    recipient_email = st.text_input("Recipient Email ID", key="email_input")

    if st.button("Send Alert Mail"):
        st.session_state["send_email"] = True


# -----------------------------
# STAGE 4: Automation (FIXED)
# -----------------------------
if st.session_state.get("send_email"):

    st.divider()
    st.header("4️⃣ Automation Results")

    recipient_email = st.session_state.get("email_input")

    if not recipient_email:
        st.error("Recipient email required.")
        st.stop()

    payload = {
        "document_text": st.session_state["extracted_text"],
        "question": st.session_state["user_question"],
        "structured_data": st.session_state["structured_data"],
        "recipient_email": recipient_email
    }

    with st.spinner("Triggering automation..."):
        try:
            r = requests.post(
                st.secrets["N8N_WEBHOOK_URL"],
                json=payload,
                timeout=60
            )

            r.raise_for_status()
            
            # Check if response has content before parsing JSON
            if not r.text:
                st.error("Webhook returned empty response. Check N8N workflow configuration.")
                st.stop()
            
            result = r.json()
            
            # Debug: Show what webhook returned
            st.write("🔍 **Webhook Response:**")
            st.json(result)

        except json.JSONDecodeError as e:
            st.error(f"Webhook returned invalid JSON: {e}. Response: {r.text}")
            st.stop()
        except Exception as e:
            st.error(f"Webhook failed: {e}")
            st.stop()

    # Safely extract response data
    final_answer = result.get("final_answer", "Not returned by webhook")
    email_body = result.get("email_body", "Not returned by webhook")
    email_status = result.get("email_status", "Not returned by webhook")

    st.subheader("📊 Final Analytical Answer")
    st.write(final_answer)

    st.subheader("📧 Generated Email Body")
    st.text_area("Email", email_body, height=200)

    st.success(f"Email Status: {email_status}")

    # reset after sending
    st.session_state["send_email"] = False
