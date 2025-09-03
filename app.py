import streamlit as st
from pathlib import Path
import base64

st.set_page_config(page_icon="🌐")
st.title("Workday Tenant URL Finder")

data = base64.b64encode(Path("CommitLogo.png").read_bytes()).decode()

st.markdown(
    f"""
    <style>
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 1000;
        background: white;         /* match your theme background */
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
        font-size: 1.8rem;         /* tune as you like */
        line-height: 1.2;
      }}
    </style>
    <div class="topbar">
      <div class="topbar-row">
        <img src="data:image/png;base64,{data}" alt="Commit logo">
        <h1></h1>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# You can remove a separate st.title() now since the topbar has the title.
# === Page content starts here ===
st.write(
    "Paste a Workday tenant ID. The app probes known data centers and shows matching URLs. "
    "Please note, you must know the actual tenant id for the tool to work, this is usually the "
    "name of the company with no spaces, but not always."
)

tenant_id = st.text_input("Tenant ID")

max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)

if st.button("Find URLs") and tenant_id:
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
