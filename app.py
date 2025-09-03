import streamlit as st
from pathlib import Path
import base64

st.set_page_config(page_title="Workday URL Finder", page_icon="🌐")

# === Fixed top-left logo ===
logo_path = Path(__file__).with_name("CommitLogo.png")  # exact case
data = base64.b64encode(logo_path.read_bytes()).decode()

st.markdown(
    f"""
    <style>
      /* Fixed logo */
      .commit-logo {{
        position: fixed;   /* fixed so it stays pinned even when scrolling */
        top: 12px;
        left: 12px;
        z-index: 1000;
      }}
      .commit-logo img {{
        width: 120px;
      }}

      /* Push the main content down so it clears the fixed logo */
      .block-container {{
        padding-top: 150px !important;   /* adjust if your logo height changes */
      }}
    </style>
    <div class="commit-logo">
      <img src="data:image/png;base64,{data}">
    </div>
    """,
    unsafe_allow_html=True
)

# Extra spacer as a fallback for Streamlit theme/DOM differences
st.markdown("<div style='height:0px'></div>", unsafe_allow_html=True)

# === Page content starts here ===
st.title("Workday Tenant URL Finder")
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
