# -*- coding: utf-8 -*-
"""
Workday URL discovery (Production + Sandbox + Preview + CC + IMPL tenants)

Behavior:
- Valid URLs may redirect.
- Only URLs that ultimately redirect to Workday Community "invalid-url" are treated as invalid:
  https://community.workday.com/invalid-url?dev=1
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

INVALID_URL_PREFIX = "https://community.workday.com/invalid-url"


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "WorkdayURLFinder/1.1 (+https://example.com)"
    })

    retries = Retry(
        total=3,
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


def _resolve_final_url(url: str, timeout: float = 1) -> str | None:
    """Return final resolved URL after redirects, or None if request fails."""
    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        return r.url
    except requests.RequestException:
        # Some servers disallow HEAD; try GET with streaming.
        try:
            r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=True)
            return r.url
        except requests.RequestException:
            return None


def is_valid_workday_url(url: str, timeout: float = 1) -> bool:
    """
    Return True if URL appears valid.

    Redirects are allowed.
    URL is invalid only if its final resolved URL is Workday Community invalid-url.
    """
    final_url = _resolve_final_url(url, timeout=timeout)
    if not final_url:
        return False
    return not final_url.startswith(INVALID_URL_PREFIX)


def find_production_url(tenant_id: str, timeout: float = 1):
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
        if is_valid_workday_url(url, timeout=timeout):
            return data_center, url

    return None, None


def find_sandbox_url_template(data_center: str):
    sandbox_templates = {
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


def find_implementation_tenants(sandbox_url_template: str, tenant_id: str, max_impl: int = 20, timeout: float = 1):
    implementation_tenants: list[tuple[str, str]] = []
    for i in range(1, max_impl + 1):
        impl_id = f"{tenant_id}{i}"
        url = sandbox_url_template.format(id=impl_id)
        if is_valid_workday_url(url, timeout=timeout):
            implementation_tenants.append((f"IMPL{i}", url))
    return implementation_tenants


def discover_all(tenant_id: str, timeout: float = 1, max_impl: int = 20) -> dict:
    """
    Convenience wrapper that attempts to discover:
    - Production data center + URL
    - Sandbox URL template (+ resolved base sandbox URL)
    - Preview + CC templates
    - IMPL tenants
    """
    result = {
        "tenant_id": tenant_id,
        "production_data_center": None,
        "production_url": None,
        "sandbox_url_template": None,
        "sandbox_url": None,
        "preview_url_template": None,
        "cc_url_template": None,
        "impl_tenants": [],
    }

    dc, prod_url = find_production_url(tenant_id, timeout=timeout)
    result["production_data_center"] = dc
    result["production_url"] = prod_url

    if not dc:
        return result

    sandbox_tpl = find_sandbox_url_template(dc)
    result["sandbox_url_template"] = sandbox_tpl

    if sandbox_tpl:
        sandbox_url = sandbox_tpl.format(id=tenant_id)
        result["sandbox_url"] = sandbox_url

        result["preview_url_template"] = find_preview_url_template(sandbox_tpl)
        result["cc_url_template"] = find_cc_url_template(sandbox_tpl)

        result["impl_tenants"] = find_implementation_tenants(
            sandbox_tpl, tenant_id, max_impl=max_impl, timeout=timeout
        )

    return result


if __name__ == "__main__":
    # Example usage:
    tenant = "yourtenant"
    info = discover_all(tenant, timeout=1.5, max_impl=20)

    print(f"Tenant: {info['tenant_id']}")
    print(f"Production DC: {info['production_data_center']}")
    print(f"Production URL: {info['production_url']}")
    print(f"Sandbox Template: {info['sandbox_url_template']}")
    print(f"Sandbox URL: {info['sandbox_url']}")
    print(f"Preview Template: {info['preview_url_template']}")
    print(f"CC Template: {info['cc_url_template']}")

    if info["impl_tenants"]:
        print("Implementation Tenants:")
        for name, url in info["impl_tenants"]:
            print(f"  {name}: {url}")
    else:
        print("Implementation Tenants: none found")
