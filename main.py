# -*- coding: utf-8 -*-
"""
Core logic for Workday URL discovery.
Derived from user's original script, with minor resiliency improvements.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _build_session():
    session = requests.Session()
    # Be polite and identify
    session.headers.update({
        "User-Agent": "WorkdayURLFinder/1.0 (+https://example.com)"
    })
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

_SESSION = _build_session()

def check_redirect(url: str, timeout: float = 1) -> bool:
    """Return True if final URL equals the requested URL (no redirect).

    Tries HEAD first, falls back to GET if HEAD is not allowed.
    """
    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        if r.is_redirect or r.history:
            return r.url == url
        return True  # no redirect at all
    except requests.RequestException:
        # Some servers disallow HEAD. Try a light GET without downloading body.
        try:
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

def find_implementation_tenants(sandbox_url_template: str, tenant_id: str, max_impl: int = 20):
    implementation_tenants = []
    for i in range(1, max_impl):
        impl_id = f"{tenant_id}{i}"
        url = sandbox_url_template.format(id=impl_id)
        if check_redirect(url):
            implementation_tenants.append((f"IMPL{i}:", url))
    return implementation_tenants
