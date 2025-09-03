import base64
import json
from pathlib import Path
import streamlit as st

from main import (
    find_production_url,
    find_sandbox_url,
    find_preview_url,
    find_cc_url,
    find_implementation_tenants,
)

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(page_title="Workday Tenant URL Finder", page_icon="CommitLogo.png")

# -------------------------------------------------
# Sticky top bar: logo + title side by side
# -------------------------------------------------
logo_b64 = base64.b64encode(Path("CommitLogo.png").read_bytes()).decode()
st.markdown(
    f"""
    <style>
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 1000;
        background: white;
        padding: 10px 12px 6px 12px;
        border-bottom: 1px solid #eee;
      }}
      .topbar-row {{
        display: flex;
        align-items: center;
        gap: 16px;
      }}
      .topbar img {{ width: 110px; display: block; }}
      .topbar h1 {{
        margin: 0;
        font-size: 1.8rem;
        line-height: 1.2;
      }}
      .copy-btn {{
        padding: 2px 6px;
        cursor: pointer;
        border: 1px solid #ddd;
        border-radius: 6px;
        background: #f9f9f9;
        font-size: 0.9rem;
      }}
      .url-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 2px 0;
        flex-wrap: wrap;
      }}
    </style>
    <div class="topbar">
      <div class="topbar-row">
        <a href="https://commitconsulting.com/" target="_blank" rel="noopener">
          <img src="data:image/png;base64,{logo_b64}" alt="Commit logo">
        </a>
        <h1>Workday Tenant URL Finder</h1>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def show_link(label: str, url: str, key: str):
    """
    Renders a labeled, clickable URL with an inline copy-to-clipboard button.
    Uses JSON encoding to safely embed the URL in JS.
    """
    js_url = json.dumps(url)  # safe for embedding in JS string
    st.markdown(
        f"""
        <div class="url-row">
          <span><strong>{label} URL:</strong> <a href="{url}" target="_blank" rel="noopener">{url}</a></span>
          <button id="copy_{key}" class="copy-btn" aria-label="Copy {label} URL">📋</button>
        </div>
        <script>
          const btn_{key} = document.getElementById("copy_{key}");
          if (btn_{key}) {{
            btn_{key}.onclick = async () => {{
              try {{
                await navigator.clipboard.writeText({js_url});
                const old = btn_{key}.innerText;
                btn_{key}.innerText = "✅";
                setTimeout(() => btn_{key}.innerText = old, 1200);
              }} catch (e) {{
                btn_{key}.innerText = "⚠️";
                setTimeout(() => btn_{key}.innerText = "📋", 1200);
              }}
            }};
          }}
        </script>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# Session state - Simple format
# -------------------------------------------------
if "search_history" not in st.session_state:
    st.session_state.search_history = {}  # {tenant_id: success_bool}
if "prefill" not in st.session_state:
    st.session_state.prefill = ""
if "run_from_history" not in st.session_state:
    st.session_state.run_from_history = False

# -------------------------------------------------
# Sidebar: recent searches
# -------------------------------------------------
with st.sidebar:
    st.subheader("Recent Searches")
    if st.session_state.search_history:
        for tenant_id, was_successful in reversed(list(st.session_state.search_history.items())):
            # Color coding
            if was_successful:
                button_label = f"🟢 {tenant_id}"
            else:
                button_label = f"🔴 {tenant_id}"
            
            if st.button(button_label, key=f"hist_{tenant_id}", use_container_width=True):
                st.session_state.prefill = tenant_id
                st.session_state.run_from_history = True
                st.rerun()
                
        if st.button("Clear History", type="secondary", use_container_width=True):
            st.session_state.search_history = {}
            st.session_state.prefill = ""
            st.rerun()
    else:
        st.caption("No searches yet")

# -------------------------------------------------
# Helper text
# -------------------------------------------------
st.info(
    "Paste a Workday tenant ID. The app probes known data centers and shows matching URLs. "
    "You must know the actual tenant id for the tool to work. Often the company name with no spaces, but not always."
)

# -------------------------------------------------
# Input form
# -------------------------------------------------
with st.form(key="search_form", clear_on_submit=False):
    current_prefill = st.session_state.prefill
    tenant_id = st.text_input("Tenant ID", value=
