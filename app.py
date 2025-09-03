import base64
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
# Session state
# -------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []     # list[str]
if "prefill" not in st.session_state:
    st.session_state.prefill = ""     # value used to prefill the input

# -------------------------------------------------
# Sidebar: recent searches (prefill only)
# -------------------------------------------------
with st.sidebar:
    st.subheader("Recent")
    if st.session_state.history:
        for t in reversed(st.session_state.history):  # newest first
            if st.button(t, key=f"hist-{t}", use_container_width=True):
                st.session_state.prefill = t  # just prefill; user must press Enter
        if st.button("Clear history", type="secondary", use_container_width=True):
            st.session_state.history = []
            st.session_state.prefill = ""
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
# Input form: pressing Enter submits the form
# -------------------------------------------------
with st.form(key="search_form", clear_on_submit=False):
    tenant_id = st.text_input("Tenant ID", value=st.session_state.prefill)
    max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)
    submitted = st.form_submit_button("Find URLs")  # Enter triggers this

# -------------------------------------------------
# Action (runs only on submit)
# -------------------------------------------------
if submitted:
    if not tenant_id:
        st.warning("Enter a tenant ID first.")
        st.stop()

    # Update history: move to end if already present, keep last 10
    if tenant_id in st.session_state.history:
        st.session_state.history.remove(tenant_id)
    st.session_state.history.append(tenant_id)
    st.session_state.history = st.session_state.history[-10:]
    st.session_state.prefill = tenant_id  # keep it in the box for convenience

    with st.spinner("Checking data centers..."):
        data_center, production_url = find_production_url(tenant_id)

    if not production_url:
        st.error("No Production URL found.")
        st.stop()

    st.metric(label="Data Center", value=data_center)
    st.success(f"[Production URL]({production_url})")

    sandbox_template = find_sandbox_url(data_center, tenant_id)

    urls_core = []  # (label, url)
    urls_impl = []  # (label, url)

    if sandbox_template:
        sx = sandbox_template.format(id=tenant_id)
        pv = find_preview_url(sandbox_template).format(id=tenant_id)
        cc = find_cc_url(sandbox_template).format(id=tenant_id)

        st.subheader("Related")
        st.write(f"[Sandbox URL]({sx})")
        st.write(f"[Preview URL]({pv})")
        st.write(f"[Customer Central URL]({cc})")

        urls_core.extend([
            ("Production", production_url),
            ("Sandbox", sx),
            ("Preview", pv),
            ("Customer Central", cc),
        ])

        with st.spinner("Scanning IMPL tenants..."):
            impls = find_implementation_tenants(sandbox_template, tenant_id, max_impl=max_impl)

        st.subheader("Implementation Tenants")
        if impls:
            for label, url in impls:
                st.write(f"{label} [{url}]({url})")
                urls_impl.append((label.strip(" :"), url))
        else:
            st.write("No implementation tenants found.")
    else:
        st.warning("No Sandbox URL found for this Data Center.")
        urls_core.append(("Production", production_url))

    # -------------------------------------------------
    # Slack-ready message with copy button
    # -------------------------------------------------
    lines = [f"*Workday URLs for `{tenant_id}`*"]
    for label, url in urls_core:
        lines.append(f"• *{label}:* <{url}>")

    if urls_impl:
        lines.append("*Implementation Tenants*")
        for label, url in urls_impl:
            lines.append(f"• *{label}:* <{url}>")

    slack_message = "\n".join(lines)

    st.subheader("Share to Slack")
    st.caption("Use the copy icon to copy the formatted message")
    st.code(slack_message, language=None)

    st.download_button(
        "Download as .txt",
        data=slack_message,
        file_name=f"workday_urls_{tenant_id}.txt",
        mime="text/plain",
    )
