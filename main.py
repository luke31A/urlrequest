# -*- coding: utf-8 -*-
"""
Core logic for Workday URL discovery.
Derived from user's original script, with minor resiliency improvements.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
from threading import Lock

def _build_session():
    session = requests.Session()
    # Be polite and identify
    session.headers.update({
        "User-Agent": "WorkdayURLFinder/1.0 (+https://example.com)"
    })
    retries = Retry(
        total=2,  # Reduced from 3 for faster failures
        backoff_factor=0.1,  # Reduced from 0.3
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

_SESSION = _build_session()
_SESSION_LOCK = Lock()

def check_redirect(url: str, timeout: float = 3.0) -> bool:  # Reduced timeout from 8.0 to 3.0
    """Return True if final URL equals the requested URL (no redirect).

    Tries HEAD first, falls back to GET if HEAD is not allowed.
    """
    try:
        with _SESSION_LOCK:  # Thread-safe session usage
            r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        if r.is_redirect or r.history:
            return r.url == url
        return True  # no redirect at all
    except requests.RequestException:
        # Some servers disallow HEAD. Try a light GET without downloading body.
        try:
            with _SESSION_LOCK:
                r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=True)
            if r.is_redirect or r.history:
                return r.url == url
            return True
        except requests.RequestException:
            return False

def find_production_url(tenant_id: str):
    data_centers = {
        "Data Center 1": "https://www.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 3": "https://wd3.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 5": "https://wd5.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 10": "https://wd10.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 12": "https://wd12.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 102": "https://wd102.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 103": "https://wd103.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 104": "https://wd104.myworkdaygov.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 105": "https://wd105.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 501": "https://wd501.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 503": "https://wd503.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n"
    }

    for data_center, url_template in data_centers.items():
        url = url_template.format(id=tenant_id)
        if check_redirect(url):
            return data_center, url
    return None, None

def find_sandbox_url(data_center: str, tenant_id: str):
    sandbox_urls = {
        "Data Center 1": "https://impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 3": "https://wd3-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 5": "https://wd5-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 10": "https://wd10-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 12": "https://impl.wd12.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 102": "https://wd102-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 103": "https://wd103-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 104": "https://wd104-impl.workdaygov.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 105": "https://wd105-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 501": "https://wd501-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 503": "https://impl.wd503.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n"
    }
    return sandbox_urls.get(data_center, None)

def find_preview_url(sandbox_url_template: str):
    # Replace '/{id}/' with '/{id}_Preview/'
    return sandbox_url_template.replace('/{id}/', '/{id}_Preview/')

def find_cc_url(sandbox_url_template: str):
    # Replace '/{id}/' with '/{id}_cc/'
    return sandbox_url_template.replace('/{id}/', '/{id}_cc/')

def check_impl_tenant(sandbox_url_template: str, tenant_id: str, impl_index: int):
    """Check a single IMPL tenant. Returns (label, url) if found, None if not."""
    impl_id = f"{tenant_id}{impl_index}"
    url = sandbox_url_template.format(id=impl_id)
    if check_redirect(url, timeout=2.0):  # Shorter timeout for IMPL checks
        return (f"IMPL{impl_index}:", url)
    return None

def find_implementation_tenants(sandbox_url_template: str, tenant_id: str, max_impl: int = 20):
    implementation_tenants = []
    consecutive_failures = 0
    max_consecutive_failures = 3  # Stop after 3 consecutive failures
    
    # Check first few sequentially to establish pattern
    for i in range(1, min(4, max_impl + 1)):
        result = check_impl_tenant(sandbox_url_template, tenant_id, i)
        if result:
            implementation_tenants.append(result)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                # No IMPL tenants found in first 3, likely none exist
                return implementation_tenants
    
    # If we found some, continue checking the rest in parallel
    if implementation_tenants and max_impl > 3:
        remaining_indices = list(range(4, max_impl + 1))
        
        # Use
