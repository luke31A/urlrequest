
import streamlit as st
from main import (
    find_production_url,
    find_sandbox_url,
    find_preview_url,
    find_cc_url,
    find_implementation_tenants,
)

st.set_page_config(page_title="Workday URL Finder", page_icon="🌐")
st.title("Workday Tenant URL Finder")

st.write("Paste a Workday tenant ID. The app probes known data centers and shows matching URLs.")

tenant_id = st.text_input("Tenant ID")

max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=20, step=1)

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
