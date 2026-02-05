# AI-Powered Document Orchestrator

A Streamlit app that analyzes uploaded documents with an AI model, extracts structured insights, and triggers an external automation (N8N webhook) to generate/send conditional alert emails.

Files
- `app.py` — main Streamlit application
- `demo.py` — simplified demo UI
- `test_api.py` — small script to test OpenRouter API
- `.streamlit/secrets.toml` — place API keys and webhook URL here (not checked into VCS)

Prerequisites
- Python 3.8+
- Internet access for API and N8N webhook calls

Install
```bash
python -m pip install --upgrade pip
pip install streamlit pdfplumber requests
```

Secrets / Configuration
Create `.streamlit/secrets.toml` containing your keys (example):

```toml
OPENROUTER_API_KEY = "PASTE_YOUR_OPENROUTER_KEY_HERE"
N8N_WEBHOOK_URL = "https://your-n8n-host/webhook/your-path"
```

Running the app
```bash
streamlit run app.py
```

Testing the webhook (PowerShell)
Use this command to POST a test payload and view the webhook response:

```powershell
$body = @{
    document_text = "Test"
    question = "Test?"
    structured_data = @{ risk_level = "High" }
    recipient_email = "test@example.com"
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://your-n8n-host/webhook/your-path" \
    -Method Post \
    -ContentType "application/json" \
    -Body $body | Select-Object -ExpandProperty Content
```

Expected webhook output
The app expects the webhook to return JSON with these keys:
```json
{
  "final_answer": "string",
  "email_body": "string",
  "email_status": "string"
}
```

Troubleshooting
- "Webhook returned empty response": The N8N workflow likely lacks a final **HTTP Response** node. Add one and set `Status Code` to `200` and a JSON `Response Body` mapping the output fields (e.g. using `{{ $json.yourField }}`).
- `KeyError: 'final_answer'`: The webhook returned JSON but without the expected keys. Use the test command above to inspect the exact response. The app now prints the raw webhook JSON for debugging.
- Invalid JSON / parse errors: Ensure the N8N HTTP Response node returns valid JSON (no extra text/html wrapper).

Notes
- Do not commit `.streamlit/secrets.toml` or any secret keys to source control.
- If you want, I can add a `requirements.txt` and a minimal N8N example workflow export — tell me which you'd prefer next.

License
- (Add your license / attribution if needed)
