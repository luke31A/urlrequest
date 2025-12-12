# -*- coding: utf-8 -*-
"""
Workday URL discovery (Production + Sandbox + Preview + CC + IMPL tenants)

Valid if:
- No redirect, OR redirects anywhere EXCEPT:
  https://community.workday.com/invalid-url?dev=1

Invalid if:
- Request fails, OR final URL equals the invalid URL above
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

INVALID_FINAL_URL = "https://community.workday.com/invalid-url?dev=1"


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "WorkdayURLFinder/1.2 (+https://example.com)"})

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


def resolve_url(url: str, timeout: float = 1.5) -> str | None:
    """
    Resolve redirects and return the final URL, or None if request fails.
    Tries HEAD first, falls back to GET (streamed) if needed.
    """
    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        return r.url
    except requests.RequestException:
        try:
            r = _SESSION.get(url, allow_redirects=True, timeout=timeout, stream=True)
            return r.url
        except requests.RequestException:
            return None


def valid_url_or_none(url: str, timeout: float = 1.5) -> str | None:
    """
    Return the final URL if valid, otherwise None.

    Valid means:
    - final URL is not the Workday community invalid URL
    """
    final_url = resolve_url(url, timeout=timeout)
    if not final_url:
        return None

    # Only treat this exact destination as invalid
    if final_url == INVALID_FINAL_URL:
        return None

    return final_url


def find_production_url(tenant_id: str, timeout: float = 1.5):
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

    for data_center, tpl in data_centers.items():
        candidate = tpl.format(id=tenant_id)
        final_url = valid_url_or_none(candidate, timeout=timeout)
        if final_url:
            # Return BOTH: the candidate you tested, and the final resolved URL
            return data_center, candidate, final_url

    return None, None, None


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
    return sandbox_url_template.replace("/{id}/", "/{id}_Preview/")


def find_cc_url_template(sandbox_url_template: str) -> str:
    return sandbox_url_template.replace("/{id}/", "/{id}_cc/")


def find_implementation_tenants(sandbox_url_template: str, tenant_id: str, max_impl: int = 20, timeout: float = 1.5):
    found: list[tuple[str, str, str]] = []
    for i in range(1, max_impl + 1):
        impl_id = f"{tenant_id}{i}"
        candidate = sandbox_url_template.format(id=impl_id)
        final_url = valid_url_or_none(candidate, timeout=timeout)
        if final_url:
            found.append((f"IMPL{i}", candidate, final_url))
    return found


def discover_all(tenant_id: str, timeout: float = 1.5, max_impl: int = 20) -> dict:
    result = {
        "tenant_id": tenant_id,
        "production_data_center": None,
        "production_candidate_url": None,
        "production_final_url": None,
        "sandbox_url_template": None,
        "sandbox_candidate_url": None,
        "sandbox_final_url": None,
        "preview_url_template": None,
        "cc_url_template": None,
        "impl_tenants": [],
    }

    dc, prod_candidate, prod_final = find_production_url(tenant_id, timeout=timeout)
    result["production_data_center"] = dc
    result["production_candidate_url"] = prod_candidate
    result["production_final_url"] = prod_final

    if not dc:
        return result

    sandbox_tpl = find_sandbox_url_template(dc)
    result["sandbox_url_template"] = sandbox_tpl

    if sandbox_tpl:
        sandbox_candidate = sandbox_tpl.format(id=tenant_id)
        sandbox_final = valid_url_or_none(sandbox_candidate, timeout=timeout)
        result["sandbox_candidate_url"] = sandbox_candidate
        result["sandbox_final_url"] = sandbox_final

        result["preview_url_template"] = find_preview_url_template(sandbox_tpl)
        result["cc_url_template"] = find_cc_url_template(sandbox_tpl)

        result["impl_tenants"] = find_implementation_tenants(
            sandbox_tpl, tenant_id, max_impl=max_impl, timeout=timeout
        )

    return result


if __name__ == "__main__":
    tenant = "yourtenant"
    info = discover_all(tenant, timeout=1.5, max_impl=20)

    print(f"Tenant: {info['tenant_id']}")
    print(f"Production DC: {info['production_data_center']}")
    print(f"Production Candidate: {info['production_candidate_url']}")
    print(f"Production Final: {info['production_final_url']}")
    print(f"Sandbox Template: {info['sandbox_url_template']}")
    print(f"Sandbox Candidate: {info['sandbox_candidate_url']}")
    print(f"Sandbox Final: {info['sandbox_final_url']}")
    print(f"Preview Template: {info['preview_url_template']}")
    print(f"CC Template: {info['cc_url_template']}")

    if info["impl_tenants"]:
        print("Implementation Tenants:")
        for name, candidate, final in info["impl_tenants"]:
            print(f"  {name}: {candidate}  ->  {final}")
    else:
        print("Implementation Tenants: none found")
