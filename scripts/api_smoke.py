#!/usr/bin/env python3
"""Smoke-check callable Repair CRM API GET endpoints from OpenAPI.

The script logs in, reads /api/openapi.json, fills common path/query parameters
from existing test data, and fails on any 4xx/5xx response. Destructive methods
are intentionally skipped.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
import urllib3

OPTIONAL_ADMIN_AGENT_PREFIX = "/api/admin-agent/support"
SYNC_PUBLIC_SHOPS_PATH = "/api/client-sync/portal-public-shops"


def unwrap_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("items") or payload.get("customers") or []
    return []


def first_id(payload: Any) -> int | None:
    rows = unwrap_list(payload)
    if rows and isinstance(rows[0], dict):
        return rows[0].get("id")
    return None


def request_json(session: requests.Session, method: str, url: str, **kwargs):
    response = session.request(method, url, timeout=20, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text[:300]
    return response, payload


def default_query_value(name: str) -> str | int:
    now = datetime.now(timezone.utc)
    defaults: dict[str, str | int] = {
        "page": 1,
        "page_size": 20,
        "limit": 10,
        "period": "30_days",
        "format": "pdf",
        "period_days": 30,
        "date_from": (now - timedelta(days=30)).isoformat(),
        "date_to": now.isoformat(),
        "device_model_id": 1,
        "active_only": "true",
        "low_stock_only": "false",
    }
    return defaults.get(name, "test")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair CRM API smoke checker")
    parser.add_argument("--base-url", default="http://127.0.0.1:4200/api")
    parser.add_argument("--username", default="b00bs")
    parser.add_argument("--password", default="QwsAzx@2000")
    parser.add_argument(
        "--host-header",
        default="",
        help="Override HTTP Host header, useful when base-url points to an IP.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for IP/Host-header smoke checks.",
    )
    parser.add_argument(
        "--sync-token",
        default="",
        help="X-Sync-Token for public client-sync endpoints.",
    )
    parser.add_argument(
        "--tenant-key",
        default="",
        help="X-Tenant-Key for public client-sync endpoints.",
    )
    parser.add_argument(
        "--strict-optional-integrations",
        action="store_true",
        help="Fail instead of skipping optional integration endpoints that are disabled.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    origin_url = base_url.removesuffix("/api")
    session = requests.Session()
    session.verify = not args.insecure
    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if args.host_header:
        session.headers.update({"Host": args.host_header})
    if args.sync_token:
        session.headers.update({"X-Sync-Token": args.sync_token})
    if args.tenant_key:
        session.headers.update({"X-Tenant-Key": args.tenant_key})

    login_response, login_payload = request_json(
        session,
        "POST",
        f"{base_url}/auth/login",
        json={"username": args.username, "password": args.password},
    )
    if login_response.status_code != 200:
        print(f"auth/login failed: {login_response.status_code} " f"{login_payload}")
        return 1

    token = login_payload["access_token"]
    user = login_payload["user"]
    current_shop = user.get("current_shop") or {}
    session.headers.update({"Authorization": f"Bearer {token}"})
    if current_shop.get("id"):
        session.headers.update({"X-Current-Shop": str(current_shop["id"])})

    context: dict[str, int] = {
        "shop_id": current_shop.get("id") or 1,
        "user_id": user["id"],
    }

    seed_endpoints = [
        ("order_id", "/orders"),
        ("customer_id", "/customers"),
        ("item_id", "/inventory/items"),
        ("supplier_id", "/inventory/suppliers"),
        ("request_id", "/inventory/purchase-requests"),
        ("role_id", "/admin/roles"),
    ]
    for key, path in seed_endpoints:
        if key == "customer_id" and context.get("customer_id"):
            continue
        response, payload = request_json(session, "GET", f"{base_url}{path}")
        if response.status_code < 400:
            found_id = first_id(payload)
            if found_id:
                context[key] = found_id
            if key == "order_id":
                rows = unwrap_list(payload)
                if rows and isinstance(rows[0], dict):
                    customer = rows[0].get("customer") or {}
                    customer_id = customer.get("id")
                    if customer_id:
                        context["customer_id"] = customer_id
            if key == "request_id":
                context["purchase_request_id"] = found_id

    if context.get("request_id"):
        response, payload = request_json(
            session,
            "GET",
            f"{base_url}/inventory/purchase-requests/{context['request_id']}",
        )
        if response.status_code < 400 and isinstance(payload, dict):
            request_items = payload.get("items") or []
            if request_items and isinstance(request_items[0], dict):
                context["request_item_id"] = request_items[0].get("id")
            batches = payload.get("batches") or []
            if batches and isinstance(batches[0], dict):
                context["batch_id"] = batches[0].get("id")

    loyalty_response, loyalty_payload = request_json(
        session, "GET", f"{base_url}/loyalty/programs"
    )
    context["loyalty_enabled"] = int(
        loyalty_response.status_code < 400 and bool(unwrap_list(loyalty_payload))
    )

    spec_response, spec = request_json(session, "GET", f"{base_url}/openapi.json")
    if spec_response.status_code != 200:
        print(f"openapi failed: {spec_response.status_code} {spec}")
        return 1

    checked: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []

    for path, methods in sorted(spec.get("paths", {}).items()):
        operation = methods.get("get")
        if not operation:
            continue
        if path in {"/", "/api/", "/openapi.json", "/api/openapi.json"}:
            continue
        if path == "/api/loyalty/customer/{customer_id}" and not context.get(
            "loyalty_enabled"
        ):
            skipped.append(f"GET {path} loyalty program is not configured")
            continue
        if (
            path == SYNC_PUBLIC_SHOPS_PATH
            and not args.sync_token
            and not args.tenant_key
        ):
            skipped.append(
                f"GET {path} requires X-Sync-Token and X-Tenant-Key"
            )
            continue

        resolved_path = path
        missing_param = None
        for parameter in operation.get("parameters", []):
            if parameter.get("in") == "path":
                name = parameter["name"]
                value = context.get(name)
                if value is None:
                    missing_param = name
                    break
                resolved_path = resolved_path.replace(f"{{{name}}}", str(value))
        if missing_param:
            skipped.append(f"GET {path} missing {missing_param}")
            continue

        query = {}
        for parameter in operation.get("parameters", []):
            if parameter.get("in") != "query":
                continue
            name = parameter["name"]
            if parameter.get("required"):
                query[name] = default_query_value(name)
            elif path.endswith("/reports/export/dashboard") and name in {
                "period",
                "format",
            }:
                query[name] = default_query_value(name)

        endpoint_url = (
            f"{origin_url}{resolved_path}"
            if resolved_path.startswith("/api/")
            else f"{base_url}{resolved_path}"
        )
        response, payload = request_json(
            session,
            "GET",
            endpoint_url,
            params=query,
        )
        checked.append(f"GET {resolved_path}")
        if response.status_code >= 400:
            if (
                not args.strict_optional_integrations
                and resolved_path.startswith(OPTIONAL_ADMIN_AGENT_PREFIX)
                and response.status_code == 502
            ):
                skipped.append(
                    f"GET {resolved_path} optional admin integration is not configured"
                )
                checked.pop()
                continue
            failures.append(
                f"GET {resolved_path} -> {response.status_code}: "
                f"{str(payload)[:220]}"
            )

    print(f"API smoke checked: {len(checked)}")
    print(f"API smoke skipped: {len(skipped)}")
    for item in skipped[:20]:
        print(f"SKIP {item}")
    if failures:
        print("API smoke failures:")
        for failure in failures:
            print(f"FAIL {failure}")
        return 1

    print("API smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
