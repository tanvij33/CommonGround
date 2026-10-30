"""Diagnostic tool for testing live Qloo Hackathon API endpoints.

Usage:
    python3 backend/qloo_debug.py
    python3 backend/qloo_debug.py --endpoint /v2/search --param query=Radiohead
    python3 backend/qloo_debug.py --endpoint /v2/insights --param filter.type=urn:entity:place --param filter.location.query=Delhi

Prints:
- Full request URL and method
- Status code
- Response headers
- First 2000 characters of the response body
- Full, unswallowed error messages on failure
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()


def get_config():
    api_key = os.getenv("QLOO_API_KEY", "").strip("\"' \t\n")
    base_url = os.getenv("QLOO_BASE_URL", "https://hackathon.api.qloo.com").strip().rstrip("/")
    mock_mode = os.getenv("QLOO_MOCK", "false").strip().lower() in ("true", "1", "yes")
    return api_key, base_url, mock_mode


def make_debug_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    headers_extra: Optional[Dict[str, str]] = None,
    timeout: float = 20.0
):
    api_key, base_url, mock_mode = get_config()
    
    print("=" * 80)
    print("  QLOO API DIAGNOSTIC REQUEST")
    print("=" * 80)
    print(f"Base URL:         {base_url}")
    print(f"QLOO_API_KEY set: {bool(api_key)} (Length: {len(api_key)})")
    print(f"QLOO_MOCK:        {os.getenv('QLOO_MOCK')} (Mock Mode Active: {mock_mode})")
    print(f"Endpoint:         {endpoint}")
    print(f"Method:           {method.upper()}")
    print(f"Params:           {params}")
    print("-" * 80)

    if not api_key:
        print("❌ ERROR: QLOO_API_KEY is missing or empty in .env.")
        print("Please set QLOO_API_KEY before running this diagnostic tool.")
        return

    # Build URL
    url = f"{base_url}{endpoint}" if endpoint.startswith("/") else f"{base_url}/{endpoint}"

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json"
    }
    if headers_extra:
        headers.update(headers_extra)

    try:
        with httpx.Client(timeout=timeout) as client:
            req = client.build_request(method.upper(), url, params=params, headers=headers)
            print(f"Full Request URL: {req.url}")
            print(f"Request Headers:  X-Api-Key: [REDACTED_KEY_LEN_{len(api_key)}], Accept: {headers.get('Accept')}")
            print("-" * 80)

            response = client.send(req)
            
            print(f"HTTP STATUS:      {response.status_code} {response.reason_phrase}")
            print("RESPONSE HEADERS:")
            for k, v in response.headers.items():
                print(f"  {k}: {v}")
            print("-" * 80)
            print("RESPONSE BODY (First 2000 chars):")
            body_text = response.text
            print(body_text[:2000])
            if len(body_text) > 2000:
                print(f"\n... [Truncated: {len(body_text) - 2000} more characters]")
            print("=" * 80)

            # Cause analysis based on status code
            diagnose_status(response.status_code, body_text)
            return response

    except httpx.ConnectError as e:
        print("\n❌ CONNECTION / NETWORK ERROR:")
        print(f"Failed to connect to {url}: {e}")
        print("Cause: Network issue, DNS failure, or base URL host unreachable.")
        raise
    except httpx.TimeoutException as e:
        print("\n❌ REQUEST TIMEOUT ERROR:")
        print(f"Request to {url} timed out after {timeout} seconds: {e}")
        print("Cause: Network issue or API server response latency.")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR ({type(e).__name__}):")
        print(f"{e}")
        raise


def diagnose_status(status_code: int, body: str):
    """Diagnoses likely cause based on status code."""
    print("\n🔍 DIAGNOSTIC ASSESSMENT:")
    if status_code in (200, 201):
        print("  ✅ Status 200 OK: Authentication accepted and endpoint responded successfully.")
    elif status_code in (401, 403):
        print("  ❌ Status 401/403 Unauthorized/Forbidden:")
        print("     Cause: missing/wrong auth header or invalid/expired API key.")
        print("     Verify that QLOO_API_KEY in .env matches the hackathon dashboard.")
    elif status_code == 404:
        print("  ❌ Status 404 Not Found:")
        print("     Cause: wrong path. Verify endpoint URL (e.g. /v2/search vs /search).")
    elif status_code == 400:
        print("  ❌ Status 400 Bad Request:")
        print("     Cause: wrong parameter names or bad entity type.")
        print(f"     Server message: {body[:300]}")
    elif status_code == 429:
        print("  ❌ Status 429 Too Many Requests:")
        print("     Cause: rate limit exceeded.")
    elif status_code >= 500:
        print(f"  ❌ Status {status_code} Server Error:")
        print("     Cause: Qloo remote server error.")
    else:
        print(f"  Status {status_code}: Inspect response body above.")


def main():
    parser = argparse.ArgumentParser(description="Test Qloo API endpoints directly.")
    parser.add_argument("--endpoint", default="/v2/search", help="Endpoint path, e.g. /v2/search or /v2/insights")
    parser.add_argument("--method", default="GET", help="HTTP method: GET or POST")
    parser.add_argument("--param", action="append", help="Query param in key=value format (can specify multiple)")
    args = parser.parse_args()

    params = {}
    if args.param:
        for p in args.param:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k] = v
    else:
        if args.endpoint == "/v2/search":
            params = {"query": "Radiohead"}
        elif args.endpoint == "/v2/insights":
            params = {"filter.type": "urn:entity:place", "filter.location.query": "Delhi", "take": 5}

    make_debug_request(args.endpoint, method=args.method, params=params)


if __name__ == "__main__":
    main()

