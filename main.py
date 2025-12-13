# -*- coding: utf-8 -*-
"""
Workday URL discovery (updated redirect logic)

Behavior:
- Follows redirects for each candidate URL
- Treats a URL as INVALID only if it resolves to:
  https://community.workday.com/invalid-url?dev=1
- Otherwise, treats it as VALID (even if it redirects)

Notes:
- Uses HEAD first (fast), falls back to GET if HEAD fails
- Retries transient errors (429/5xx)
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


INVALID_URL = "https://community.workday.com/invalid-url?dev=1"


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


def is_valid_workday_url(url: str, timeout: float = 1.5) -> bool:
    """
    Return True unless the final resolved URL is Workday's known invalid URL.
    Redirects are expected and allowed.
    """
    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        return r.url != INVALID_URL

    except requests.RequestException:
        # Some servers disallow HEAD; fall back to GET without downloading body.
        try:
            r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=True)
            return r.url != INVALID_URL
        except requests.RequestException:
            return False


def find_production_url(tenant_id: str, timeout: float = 1.5):
    data_centers = {
        "Data Center 1":   "https://www.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 3":   "https://wd3.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 5":   "https://wd5.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 10":  "https://wd10.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 12":  "https://wd12.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
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
        if is_valid_workday_url(url, timeout=timeout):
            return data_center, url

    return None, None


def find_sandbox_url_template(data_center: str):
    """
    Returns the sandbox URL TEMPLATE for the selected data center.
    (You still need to call .format(id=tenant_id) to produce the actual URL.)
    """
    sandbox_templates = {
        "Data Center 1":   "https://impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 3":   "https://wd3-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 5":   "https://wd5-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 10":  "https://wd10-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 12":  "https://impl.wd12.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 102": "https://wd102-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 103": "https://wd103-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 104": "https://wd104-impl.workdaygov.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 105": "https://wd105-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 501": "https://wd501-impl.workday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 503": "https://impl.wd503.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 108": "https://impl.wd108.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
        "Data Center 107": "https://impl.wd107.myworkday.com/wday/authgwy/{id}/login.htmld?redirect=n",
    }
    return sandbox_templates.get(data_center)


def find_preview_url_template(sandbox_url_template: str) -> str:
    # Replace '/{id}/' with '/{id}_Preview/'
    return sandbox_url_template.replace("/{id}/", "/{id}_Preview/")


def find_cc_url_template(sandbox_url_template: str) -> str:
    # Replace '/{id}/' with '/{id}_cc/'
    return sandbox_url_template.replace("/{id}/", "/{id}_cc/")


def find_implementation_tenants(
    sandbox_url_template: str,
    tenant_id: str,
    max_impl: int = 20,
    timeout: float = 1.5
):
    """
    Returns list of tuples: [("IMPL1:", url), ("IMPL2:", url), ...]
    Only includes tenants whose URL does NOT resolve to INVALID_URL.
    """
    implementation_tenants = []
    for i in range(1, max_impl + 1):
        impl_id = f"{tenant_id}{i}"
        url = sandbox_url_template.format(id=impl_id)
        if is_valid_workday_url(url, timeout=timeout):
            implementation_tenants.append((f"IMPL{i}:", url))
    return implementation_tenants


def discover_workday_urls(tenant_id: str, timeout: float = 1.5, max_impl: int = 20):
    """
    Convenience wrapper that returns a dict of discovered URLs.
    """
    result = {
        "tenant_id": tenant_id,
        "production": None,
        "data_center": None,
        "sandbox": None,
        "preview": None,
        "cc": None,
        "implementation_tenants": [],
    }

    data_center, prod_url = find_production_url(tenant_id, timeout=timeout)
    result["data_center"] = data_center
    result["production"] = prod_url

    if not data_center:
        return result

    sandbox_template = find_sandbox_url_template(data_center)
    if not sandbox_template:
        return result

    sandbox_url = sandbox_template.format(id=tenant_id)
    if is_valid_workday_url(sandbox_url, timeout=timeout):
        result["sandbox"] = sandbox_url
        result["preview"] = find_preview_url_template(sandbox_template).format(id=tenant_id)
        result["cc"] = find_cc_url_template(sandbox_template).format(id=tenant_id)

    result["implementation_tenants"] = find_implementation_tenants(
        sandbox_template,
        tenant_id,
        max_impl=max_impl,
        timeout=timeout,
    )

    return result


if __name__ == "__main__":
    # Example usage:
    # tenant = "yourTenant"
    # print(discover_workday_urls(tenant))
    pass
