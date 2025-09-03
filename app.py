import base64
import json
from pathlib import Path
import streamlit as st
from streamlit.components.v1 import html

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
def show_link(label: str, url: str):
    st.markdown(
        f"**{label} URL:** <a href='{url}' target='_blank' rel='noopener'>{url}</a>",
        unsafe_allow_html=True,
    )

def copy_to_clipboard_button(label: str, text: str, key: str = "copybtn"):
    payload = json.dumps(text)  # escape safely
    html(
        f"""
        <button id="{key}"
                onclick="navigator.clipboard.writeText({payload});
                         this.innerText='Copied!';
                         setTimeout(()=>this.innerText='{label}', 1500);"
                style="padding:8px 12px; border:1px solid #ddd;
                       border-radius:6px; background:#f6f6f6; cursor:pointer;">
            {label}
        </button>
        """,
        height=45,
    )

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []     # list[str]
if "prefill" not in st.session_state:
    st.session_state.prefill = ""     # value used to prefill the input
if "run_from_history" not in st.session_state:
    st.session_state.run_from_history = False  # trigger auto-submit once

# -------------------------------------------------
# Sidebar: recent searches (click = prefill + auto-submit)
# -------------------------------------------------
with st.sidebar:
    st.subheader("Recent")
    if st.session_state.history:
        for t in reversed(st.session_state.history):  # newest first
            if st.button(t, key=f"hist-{t}", use_container_width=True):
                st.session_state.prefill = t
                st.session_state.run_from_history = True  # will submit after form renders
        if st.button("Clear history", type="secondary", use_container_width=True):
            st.session_state.history = []
            st.session_state.prefill = ""
            st.session_state.run_from_history = False
    else:
        st.caption("No recent searches yet")

# -------------------------------------------------
# Helper text
# -------------------------------------------------
st.info(
    "Paste a Workday tenant ID. The app probes known data centers and shows matching URLs. "
    "You must know the actual tenant id for the tool to work. Often the company name with no spaces, but not always."
)

# -------------------------------------------------
# Input form: Enter submits
# -------------------------------------------------
with st.form(key="search_form", clear_on_submit=False):
    # Get the current prefill value and then clear it to prevent it from sticking
    current_prefill = st.session_state.prefill
    tenant_id = st.text_input("Tenant ID", value=current_prefill)
    max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)
    submitted = st.form_submit_button("Find URLs")  # Enter triggers this

# Clear prefill after the form is rendered to prevent it from persisting
if not st.session_state.run_from_history:
    st.session_state.prefill = ""

# If a history item was clicked, auto-run once with that value
if st.session_state.run_from_history:
    submitted = True
    tenant_id = current_prefill
    st.session_state.run_from_history = False  # consume the flag

# -------------------------------------------------
# Action (runs only on submit / auto-submit)
# -------------------------------------------------
if submitted:
    if not tenant_id:
        st.warning("Enter a tenant ID first.")
        st.stop()

    # Update history: move to end if present, keep last 10
    if tenant_id in st.session_state.history:
        st.session_state.history.remove(tenant_id)
    st.session_state.history.append(tenant_id)
    st.session_state.history = st.session_state.history[-10:]
    # Don't set prefill here anymore - let it stay empty for next search

    with st.spinner("Checking data centers..."):
        data_center, production_url = find_production_url(tenant_id)

    if not production_url:
        st.error("No Production URL found.")
        st.stop()

    st.subheader(f"Results for: {tenant_id}")
    st.metric(label="Data Center", value=data_center)

    st.subheader("Core URLs")
    show_link("Production", production_url)
    copy_to_clipboard_button("Copy Production URL", production_url, key="copy_prod")

    sandbox_template = find_sandbox_url(data_center, tenant_id)

    urls_core = [("Production", production_url)]
    urls_impl = []

    if sandbox_template:
        sandbox_url = sandbox_template.format(id=tenant_id)
        preview_url = find_preview_url(sandbox_template).format(id=tenant_id)
        cc_url = find_cc_url(sandbox_template).format(id=tenant_id)

        show_link("Sandbox", sandbox_url)
        copy_to_clipboard_button("Copy Sandbox URL", sandbox_url, key="copy_sandbox")
        
        show_link("Preview", preview_url)
        copy_to_clipboard_button("Copy Preview URL", preview_url, key="copy_preview")
        
        show_link("Customer Central", cc_url)
        copy_to_clipboard_button("Copy CC URL", cc_url, key="copy_cc")

        urls_core.extend([
            ("Sandbox", sandbox_url),
            ("Preview", preview_url),
            ("Customer Central", cc_url),
        ])

        with st.spinner("Scanning IMPL tenants..."):
            impls = find_implementation_tenants(sandbox_template, tenant_id, max_impl=max_impl)

        st.subheader("Implementation Tenants")
        if impls:
            for idx, (label, url) in enumerate(impls):
                st.markdown(
                    f"{label} <a href='{url}' target='_blank' rel='noopener'>{url}</a>",
                    unsafe_allow_html=True
                )
                copy_to_clipboard_button(f"Copy {label.strip(' :')}", url, key=f"copy_impl_{idx}")
                urls_impl.append((label.strip(" :"), url))
        else:
            st.text("No implementation tenants found.")
            
        # Copy All URLs button
        st.subheader("Copy All URLs")
        all_urls = []
        for label, url in urls_core:
            all_urls.append(f"{label}: {url}")
        for label, url in urls_impl:
            all_urls.append(f"{label}: {url}")
        
        all_urls_text = "\n".join(all_urls)
        copy_to_clipboard_button("Copy All URLs", all_urls_text, key="copy_all")
        
    else:
        st.warning("No Sandbox URL found for this Data Center.")
