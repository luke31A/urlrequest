
# Workday Tenant URL Finder

Streamlit app that discovers Workday Production, Sandbox, Preview, Customer Central, and IMPL tenant URLs for a given tenant ID.

## Local run

1. Create and activate a virtual environment.
   - Windows:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - macOS or Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch:
   ```bash
   streamlit run app.py
   ```

Open the shown local URL in your browser.

## Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repo.
2. Go to https://streamlit.io/cloud and create a new app, pointing to `app.py` on your repo and branch.
3. The platform will install from `requirements.txt` and serve your app at `https://<your-app>.streamlit.app`.

## Notes

- The app sends HTTP HEAD or light GET requests to known Workday login gateways. Some environments may block HEAD. The code falls back to GET with redirects allowed and short timeouts.
- If you hit rate limits or occasional 429 or 5xx responses, the session includes basic retries.
- You can adjust the IMPL scan range via the slider.
