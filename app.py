#Comment - Written with Claude off original main.py from Luke Adams

import base64
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

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
        font-size: 1.7rem;
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
def show_link(label: str, url: str, key: str):
    js_url = json.dumps(url)
    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin:2px 0;flex-wrap:wrap;
                    font-family: var(--font, 'Source Sans Pro', sans-serif);
                    font-size: 0.75rem; line-height: 1.3;">
          <span><strong>{label} URL:</strong> 
            <a href={js_url} target="_blank" rel="noopener" 
               style="color: var(--link-color, #0366d6); text-decoration: none;">
               {url}
            </a>
          </span>
          <button id="copy_{key}"
                  style="padding:2px 6px;cursor:pointer;border:1px solid #ddd;
                         border-radius:6px;background:#f9f9f9;font-size:0.85rem;">
            📋
          </button>
        </div>
        <script>
          const btn = document.getElementById("copy_{key}");
          if (btn) {{
            btn.addEventListener("click", async () => {{
              try {{
                await navigator.clipboard.writeText({js_url});
                const old = btn.innerText;
                btn.innerText = "✅";
                setTimeout(() => btn.innerText = old, 1200);
              }} catch (e) {{
                btn.innerText = "⚠️";
                setTimeout(() => btn.innerText = "📋", 1200);
              }}
            }});
          }}
        </script>
        """,
        height=44,
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
    tenant_id = st.text_input("Tenant ID", value=current_prefill)
    max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)
    st.caption("Tip: Max IMPL index is how deep we check IMPL-XX. Increase only if you expect many implementation tenants.")
    submitted = st.form_submit_button("Find URLs")

# Clear prefill after form renders
if not st.session_state.run_from_history:
    st.session_state.prefill = ""

# Handle history click
if st.session_state.run_from_history:
    submitted = True
    tenant_id = current_prefill
    st.session_state.run_from_history = False

# -------------------------------------------------
# Main search logic
# -------------------------------------------------
if submitted:
    if not tenant_id:
        st.warning("Enter a tenant ID first.")
        st.stop()

    # Add to history (initially as failed, will update if successful)
    st.session_state.search_history[tenant_id] = False

    with st.spinner("Checking data centers..."):
        data_center, production_url = find_production_url(tenant_id)

    if not production_url:
        st.error("No Production URL found.")
        # Show angry Pikachu at bottom
        st.image("pika_angry.png", width=75)
        st.stop()

    # Mark as successful
    st.session_state.search_history[tenant_id] = True
    
    # Keep only last 10 searches
    if len(st.session_state.search_history) > 10:
        oldest_key = next(iter(st.session_state.search_history))
        del st.session_state.search_history[oldest_key]

    st.subheader(f"Results for: {tenant_id}")
    st.metric(label="Data Center", value=data_center)

    st.subheader("Core URLs")
    show_link("Production", production_url, key="prod")

    sandbox_template = find_sandbox_url(data_center, tenant_id)
    
    all_urls = [f"Production: {production_url}"]

    if sandbox_template:
        sandbox_url = sandbox_template.format(id=tenant_id)
        preview_url = find_preview_url(sandbox_template).format(id=tenant_id)
        cc_url = find_cc_url(sandbox_template).format(id=tenant_id)

        show_link("Sandbox", sandbox_url, key="sb")
        show_link("Preview", preview_url, key="pv")
        show_link("Customer Central", cc_url, key="cc")

        all_urls.extend([
            f"Sandbox: {sandbox_url}",
            f"Preview: {preview_url}",
            f"Customer Central: {cc_url}"
        ])

        with st.spinner("Scanning IMPL tenants..."):
            impls = find_implementation_tenants(sandbox_template, tenant_id, max_impl=max_impl)

        st.subheader("Implementation Tenants")
        if impls:
            for idx, (label, url) in enumerate(impls):
                clean_label = label.strip(" :")
                show_link(clean_label, url, key=f"impl_{idx}")
                all_urls.append(f"{clean_label}: {url}")
        else:
            st.text("No implementation tenants found.")
            
        # All URLs summary
        st.subheader("All URLs Summary")
        all_urls_text = "\n".join(all_urls)
        st.code(all_urls_text, language=None)
        
    else:
        
        st.warning("No Sandbox URL found for this Data Center.")
    
    # Show happy Pikachu at bottom for successful result
    st.image("pikachu_happy.png", width=75)
