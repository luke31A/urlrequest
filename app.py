#Comment - Written with Claude off original main.py from Luke Adams

import base64
import json
import re
from pathlib import Path
from typing import List
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
# Persistent Storage Functions
# -------------------------------------------------
HISTORY_FILE = "search_history.json"

def load_search_history() -> dict:
    """Load search history from file."""
    try:
        if Path(HISTORY_FILE).exists():
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading history: {e}")
    return {}

def save_search_history(history: dict):
    """Save search history to file."""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

# -------------------------------------------------
# Tenant ID Suggestion Functions
# -------------------------------------------------
def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)."""
    str1, str2 = str1.lower(), str2.lower()
    
    # Exact match
    if str1 == str2:
        return 1.0
    
    # One contains the other
    if str1 in str2 or str2 in str1:
        return 0.9
    
    # Calculate Levenshtein-like similarity (simple version)
    # Count matching characters
    matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))
    max_len = max(len(str1), len(str2))
    
    if max_len == 0:
        return 0.0
    
    return matches / max_len

def get_similar_successful_tenants(search_term: str, history: dict, threshold: float = 0.5, max_suggestions: int = 3) -> List[str]:
    """Find successful tenant IDs similar to the search term."""
    if not search_term or not history:
        return []
    
    # Get only successful searches
    successful = [tid for tid, success in history.items() if success]
    
    if not successful:
        return []
    
    # Calculate similarity scores
    scores = [(tid, calculate_similarity(search_term, tid)) for tid in successful]
    
    # Filter by threshold and sort by score
    similar = [(tid, score) for tid, score in scores if score >= threshold]
    similar.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches (tid only)
    return [tid for tid, score in similar[:max_suggestions]]

def generate_tenant_id_suggestions(original_id: str) -> List[str]:
    """Generate intelligent variations of a tenant ID."""
    suggestions = set()
    cleaned = original_id.strip().lower()
    
    if not cleaned:
        return []
    
    # Remove all spaces
    no_spaces = cleaned.replace(" ", "")
    if no_spaces != cleaned:
        suggestions.add(no_spaces)
    
    # Remove special characters (keep only alphanumeric)
    alphanumeric = re.sub(r'[^a-z0-9]', '', cleaned)
    if alphanumeric != cleaned and alphanumeric:
        suggestions.add(alphanumeric)
    
    # Remove common suffixes
    common_suffixes = ['corp', 'corporation', 'company', 'inc', 'incorporated', 
                       'llc', 'ltd', 'limited', 'group', 'international']
    for suffix in common_suffixes:
        if cleaned.endswith(f" {suffix}"):
            base = cleaned.replace(f" {suffix}", "").replace(" ", "")
            suggestions.add(base)
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
            base = cleaned[:-len(suffix)].replace(" ", "")
            suggestions.add(base)
    
    # Common abbreviations - always remove spaces
    if "corporation" in cleaned:
        suggestions.add(cleaned.replace("corporation", "corp").replace(" ", ""))
    if "company" in cleaned:
        suggestions.add(cleaned.replace("company", "co").replace(" ", ""))
    if "incorporated" in cleaned:
        suggestions.add(cleaned.replace("incorporated", "inc").replace(" ", ""))
    if "international" in cleaned:
        suggestions.add(cleaned.replace("international", "intl").replace(" ", ""))
    
    # Remove "the" prefix
    if cleaned.startswith("the "):
        suggestions.add(cleaned[4:].replace(" ", ""))
    
    # Remove trailing numbers
    if re.search(r'\d+$', cleaned):
        suggestions.add(re.sub(r'\d+$', '', cleaned).replace(" ", "").rstrip())
    
    # Multi-word patterns
    words = cleaned.split()
    if len(words) > 1:
        # All lowercase concatenated
        suggestions.add(''.join(words))
        # First word only
        suggestions.add(words[0])
        # Acronym
        if len(words) <= 5:
            acronym = ''.join(word[0] for word in words if word)
            if len(acronym) >= 2:
                suggestions.add(acronym)
    
    # Handle "&"
    if "&" in cleaned:
        suggestions.add(cleaned.replace("&", "and").replace(" ", ""))
        suggestions.add(cleaned.replace("&", "").replace(" ", ""))
        suggestions.add(cleaned.replace(" & ", "").replace(" ", ""))
    
    # Filter: remove original, empty strings, short strings, and anything with spaces or punctuation
    suggestions.discard(cleaned)
    suggestions.discard(original_id.lower())
    # Only keep suggestions that are alphanumeric (no spaces, no punctuation)
    suggestions = {s for s in suggestions if s and len(s) >= 2 and s.isalnum()}
    
    return sorted(suggestions, key=lambda x: (len(x), x))[:8]

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
      @keyframes spin {{
        from {{ transform: rotate(0deg); }}
        to   {{ transform: rotate(360deg); }}
      }}
      .logo-spin {{
        animation: spin 2s linear infinite;
        width: 80px;
        display: block;
        margin: 0 auto;
      }}
      .loading-block {{
        text-align: center;
        margin: 20px 0;
        font-size: 1rem;
        color: #444;
      }}

      /* Progress bar styles */
      .progress-wrap {{
        margin: 8px 0 20px 0;
      }}
      .progress-label {{
        font-size: 0.95rem;
        color: #444;
        margin-bottom: 6px;
        text-align: center;
      }}
      .progress {{
        width: 100%;
        height: 10px;
        background: #eee;
        border-radius: 6px;
        overflow: hidden;
      }}
      .progress-bar {{
        height: 100%;
        width: 40%;
        background: linear-gradient(90deg, #0d6efd, #66b2ff);
        border-radius: 6px;
        animation: indeterminate 1.2s infinite;
      }}
      @keyframes indeterminate {{
        0%   {{ transform: translateX(-100%); width: 40%; }}
        50%  {{ transform: translateX(25%);  width: 50%; }}
        100% {{ transform: translateX(100%); width: 40%; }}
      }}
      .progress-complete {{
        height: 100%;
        width: 100%;
        background: #22c55e; /* green */
        border-radius: 6px;
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

def show_spinner(message: str):
    """Custom Commit logo spinner block."""
    st.markdown(
        f"""
        <div class="loading-block">
          <img src="data:image/png;base64,{logo_b64}" class="logo-spin" />
          <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def show_indeterminate_progress(placeholder, label_text: str):
    """Render an animated indeterminate progress bar inside a placeholder."""
    placeholder.markdown(
        f"""
        <div class="progress-wrap">
          <div class="progress-label">{label_text}</div>
          <div class="progress">
            <div class="progress-bar"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def show_progress_complete(placeholder, label_text: str):
    """Replace the animated bar with a full green bar."""
    placeholder.markdown(
        f"""
        <div class="progress-wrap">
          <div class="progress-label">{label_text}</div>
          <div class="progress">
            <div class="progress-complete"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------------------------
# Session state - Simple format
# -------------------------------------------------
if "search_history" not in st.session_state:
    # Load from file on first run
    st.session_state.search_history = load_search_history()
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
            save_search_history({})  # Clear the saved file too
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
# Check if we should use a prefilled value
form_value = st.session_state.prefill if st.session_state.prefill else ""

with st.form(key="search_form", clear_on_submit=False):
    tenant_id = st.text_input("Tenant ID", value=form_value, key="tenant_input")
    max_impl = st.slider("Max IMPL index to probe", min_value=5, max_value=50, value=10, step=1)
    st.caption("Tip: Max IMPL index is how deep we check IMPL-XX. Increase only if you expect many implementation tenants.")
    submitted = st.form_submit_button("Find URLs")

# Handle history click
if st.session_state.run_from_history and not submitted:
    submitted = True
    tenant_id = st.session_state.prefill
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
    save_search_history(st.session_state.search_history)  # Save immediately

    # Custom spinner for production lookup
    prod_placeholder = st.empty()
    with prod_placeholder.container():
        show_spinner("Checking data centers...")

    data_center, production_url = find_production_url(tenant_id)
    prod_placeholder.empty()

    if not production_url:
        st.error("❌ No Production URL found.")
        
        # Clear prefill so it doesn't interfere
        st.session_state.prefill = ""
        
        # First, check for similar successful tenant IDs
        similar_tenants = get_similar_successful_tenants(
            tenant_id, 
            st.session_state.search_history,
            threshold=0.5,
            max_suggestions=3
        )
        
        if similar_tenants:
            st.info("💡 Found similar tenant IDs that worked before:")
            similar_text = ", ".join([f"`{s}`" for s in similar_tenants])
            st.markdown(similar_text)
            st.caption("These tenant IDs worked previously and are similar to your search.")
        
        # Generate standard suggestions
        suggestions = generate_tenant_id_suggestions(tenant_id)
        
        if suggestions:
            st.warning("🤔 Couldn't find that tenant ID. Here are some variations to try:")
            
            # Display suggestions as text with code formatting
            suggestion_text = ", ".join([f"`{s}`" for s in suggestions])
            st.markdown(suggestion_text)
            st.caption("Copy and paste one of the suggestions above into the search box.")
        
        # Show helpful tips
        with st.expander("💡 Tips for finding the correct Tenant ID"):
            st.markdown("""
            - **Remove all spaces** (e.g., "Acme Corp" → "acmecorp")
            - **Remove special characters** and punctuation
            - Try the company name **without suffixes** like "Inc", "LLC", "Corporation"
            - Some companies use **abbreviations or acronyms**
            - The tenant ID is usually **lowercase**
            - Check in your **Zendesk** if unsure
            """)
        
        # Angry Pikachu at bottom
        st.image("pika_angry.png", width=150)
        st.stop()

    # Mark as successful
    st.session_state.search_history[tenant_id] = True
    
    # Keep only last 10 searches
    if len(st.session_state.search_history) > 10:
        oldest_key = next(iter(st.session_state.search_history))
        del st.session_state.search_history[oldest_key]
    
    # Save to file after successful search
    save_search_history(st.session_state.search_history)

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

        # Indeterminate progress while scanning IMPL tenants
        impl_progress_ph = st.empty()
        show_indeterminate_progress(impl_progress_ph, "Scanning IMPL tenants...")

        impls = find_implementation_tenants(sandbox_template, tenant_id, max_impl=max_impl)

        # Flip to completed bar
        show_progress_complete(impl_progress_ph, "Scanning IMPL tenants... done")

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
    
    # Happy Pikachu at bottom on success
    st.image("pikachu_happy.png", width=150)
