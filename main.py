# -*- coding: utf-8 -*-
"""
Core logic for Workday URL discovery.

UPDATED BEHAVIOR:
- Redirects are allowed and expected.
- A candidate URL is considered INVALID only if it ultimately resolves to:
  https://community.workday.com/invalid-url?dev=1
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def check_redirect(url: str, timeout: float = 1.5) -> bool:
    """
    BACKWARDS-COMPATIBLE NAME.

    Returns True if the URL is considered valid.
    A URL is invalid only if the final resolved URL equals INVALID_URL.
    """
    invalid_norm = _normalize_url(INVALID_URL)

    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        return _normalize_url(r.url) != invalid_norm

    except requests.RequestException:
        # Fallback: Some servers disallow HEAD. Try GET without downloading body.
        try:
            r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=True)
            return _normalize_url(r.url) != invalid_norm
        except requests.RequestException:
            return False


# Optional alias (in case you started importing this name elsewhere)
def is_valid_workday_url(url: str, timeout: float = 1.5) -> bool:
    return check_redirect(url, timeout=timeout)


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
        "Data Center 503": "https://wd503.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 108": "https://wd108.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 107": "https://wd107.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
    }

    for data_center, url_template in data_centers.items():
        url = url_template.format(id=tenant_id)
        if check_redirect(url):
            return data_center, url

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
    implementation_tenants = []
    for i in range(1, max_impl + 1):
        impl_id = f"{tenant_id}{i}"
        url = sandbox_url_template.format(id=impl_id)
        if check_redirect(url):
            implementation_tenants.append((f"IMPL{i}:", url))
    return implementation_tenants
