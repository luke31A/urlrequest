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
# Make sure the filename and case match exactly
logo_b64 = base64.b64encode(Path("CommitLogo.png").read_bytes()).decode()

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
        background: white;     /* match your theme if needed */
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
# Helper text
# -------------------------------------------------
st.write(
    "Paste a Workday tenant ID. The app probes known data centers and shows matching URLs. "
    "You must know the actual tenant id for the tool to work. It is often the company name with no spaces, "
    "but not always."
)

# -------------------------------------------------
# Input form: pressing Enter submits the form
# -------------------------------------------------
with st.form(key="search_form", clear_on_submit=False):
    tenant_id = st.text_input("Tenant ID")
    max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)
    submitted = st.form_submit_button("Find URLs")

# -------------------------------------------------
# Action
# -------------------------------------------------
if submitted:
    if not tenant_id:
        st.warning("Enter a tenant ID first.")
    else:
        with st.spinner("Checking data centers..."):
            data_center, production_url = find_production_url(tenant_id)

        if production_url:
            st.success(f"Production URL: {production_url}")

            sandbox_template = find_sandbox_url(data_center, tenant_id)
            if sandbox_template:
                st.subheader("Related")
                st.write(f"Sandbox URL: {sandbox_template.format(id=tenant_id)}")
                st.write(f"Preview URL: {find_preview_url(sandbox_template).format(id=tenant_id)}")
                st.write(f"Customer Central URL: {find_cc_url(sandbox_template).format(id=tenant_id)}")

                with st.spinner("Scanning IMPL tenants..."):
                    impls = find_implementation_tenants(sandbox_template, tenant_id, max_impl=max_impl)

                st.subheader("Implementation Tenants")
                if impls:
                    for label, url in impls:
                        st.write(f"{label} {url}")
                else:
                    st.write("No implementation tenants found.")
            else:
                st.error("No Sandbox URL found for this Data Center.")
        else:
            st.error("No Production URL found.")
