# -*- coding: utf-8 -*-
"""
Core logic for Workday URL discovery.

UPDATED BEHAVIOR:
- Redirects are allowed and expected.
- A candidate URL is considered INVALID if it either:
  1. Ultimately resolves to: https://community.workday.com/invalid-url?dev=1
  2. Returns a JSON response with "failover": false
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

INVALID_URL = "https://community.workday.com/invalid-url?dev=1"


def _normalize_url(u: str) -> str:
    """Normalize URLs for comparison (handles trailing slash differences)."""
    if not u:
        return u
    return u.rstrip("/")


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "WorkdayURLFinder/2.0 (+https://example.com)"
    })

    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_SESSION = _build_session()


def check_redirect(url: str, timeout: float = 2.0) -> bool:
    """
    Returns True if the URL is considered valid.
    A URL is invalid if:
    1. The final resolved URL equals INVALID_URL, OR
    2. The response contains JSON with "failover": false
    
    ALWAYS uses GET request to check response body for JSON error patterns.
    """
    invalid_norm = _normalize_url(INVALID_URL)

    try:
        # Use GET request to be able to check response body
        # Set stream=False to read the full response
        r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=False)
        
        # Check for redirect to invalid-url
        if _normalize_url(r.url) == invalid_norm:
            return False
        
        # Check for bad HTTP status
        if r.status_code >= 400:
            return False
        
        # Check content type and parse JSON if applicable
        content_type = r.headers.get('Content-Type', '').lower()
        
        # If it's JSON, check for error patterns
        if 'application/json' in content_type or 'text/json' in content_type:
            try:
                data = r.json()
                
                # Check for the specific failover: false pattern
                if 'failover' in data and data['failover'] is False:
                    return False
                
                # Check for error messages
                if 'errorMessage' in data:
                    return False
                    
            except (ValueError, AttributeError, TypeError):
                # If JSON parsing fails, continue with text check
                pass
        
        # Fallback: Check raw text for error patterns
        if r.text:
            text_content = r.text.strip()
            
            # Check if response starts with JSON-like error
            if text_content.startswith('{'):
                # Try to detect failover:false pattern even if content-type is wrong
                if '"failover":false' in text_content or '"failover": false' in text_content:
                    return False
                if '"errorMessage"' in text_content:
                    return False
        
        # If we got here with 2xx status and no error patterns, it's valid
        return 200 <= r.status_code < 300
        
    except requests.RequestException as e:
        # Network errors mean the URL is not accessible
        return False


# Optional alias (in case you started importing this name elsewhere)
def is_valid_workday_url(url: str, timeout: float = 2.0) -> bool:
    return check_redirect(url, timeout=timeout)


def find_production_url(tenant_id: str):
    """
    Find production URL by checking all data centers in parallel.
    Returns (data_center_name, url) if found, otherwise (None, None).
    """
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
        "Data Center 503": "https://wd503.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 108": "https://wd108.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 107": "https://wd107.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
    }

    # Check all data centers in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all checks
        future_to_dc = {
            executor.submit(check_redirect, url_template.format(id=tenant_id)): (data_center, url_template)
            for data_center, url_template in data_centers.items()
        }
        
        # Return the first successful match
        for future in as_completed(future_to_dc):
            data_center, url_template = future_to_dc[future]
            try:
                if future.result():
                    # Cancel remaining futures for efficiency
                    for f in future_to_dc:
                        f.cancel()
                    return data_center, url_template.format(id=tenant_id)
            except Exception:
                # If one check fails, continue with others
                continue

    return None, None


def find_sandbox_url(data_center: str, tenant_id: str):
    """
    NOTE: Preserves your original behavior: returns the TEMPLATE for the data center,
    not a formatted URL. (tenant_id is unused here to maintain compatibility.)
    """
    sandbox_urls = {
        "Data Center 1": "https://wd2-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 3": "https://wd3-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 5": "https://wd5-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 10": "https://wd10-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 12": "https://impl.wd12.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 102": "https://wd102-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 103": "https://wd103-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 104": "https://wd104-impl-identity.workdaygov.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 105": "https://wd105-impl-identity.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 501": "https://impl-identity.wd501.myworkday.com/wday/authgwy/{id}/upc/login?redirect=n",
        "Data Center 503": "https://impl-identity.wd503.myworkday.com/wday/authgwy/{id}/upc/login?redirect=n",
        "Data Center 108": "https://impl-identity.wd108.myworkday.com/wday/authgwy/{id}/upc/login?redirect=n",
        "Data Center 107": "https://impl-identity.wd107.myworkday.com/wday/authgwy/{id}/upc/login?redirect=n",
    }
    return sandbox_urls.get(data_center, None)


def find_preview_url(sandbox_url_template: str):
    # Replace '/{id}/' with '/{id}_Preview/'
    return sandbox_url_template.replace('/{id}/', '/{id}_Preview/')


def find_cc_url(sandbox_url_template: str):
    # Replace '/{id}/' with '/{id}_cc/'
    return sandbox_url_template.replace('/{id}/', '/{id}_cc/')


def find_implementation_tenants(sandbox_url_template: str, tenant_id: str, max_impl: int = 20):
    """
    Find implementation tenants in parallel for much faster scanning.
    """
    implementation_tenants = []
    
    # Prepare all URLs to check
    urls_to_check = []
    for i in range(1, max_impl + 1):
        impl_id = f"{tenant_id}{i}"
        url = sandbox_url_template.format(id=impl_id)
        urls_to_check.append((i, impl_id, url))
    
    # Check all URLs in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_impl = {
            executor.submit(check_redirect, url): (i, impl_id, url)
            for i, impl_id, url in urls_to_check
        }
        
        for future in as_completed(future_to_impl):
            i, impl_id, url = future_to_impl[future]
            try:
                if future.result():
                    implementation_tenants.append((f"IMPL{i}:", url))
            except Exception:
                # Skip failed checks
                continue
    
    # Sort by IMPL number to maintain order
    implementation_tenants.sort(key=lambda x: int(x[0].replace("IMPL", "").replace(":", "")))
    
    return implementation_tenants
