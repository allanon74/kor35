"""
Chiamate HTTP all'API PayPal Orders v2 (token + crea ordine + capture).
"""

from __future__ import annotations

import base64
import logging
from decimal import Decimal
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _api_base(*, sandbox: bool) -> str:
    return "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"


def paypal_get_access_token(*, client_id: str, client_secret: str, sandbox: bool) -> str:
    if not client_id or not client_secret:
        raise ValueError("Credenziali PayPal incomplete")
    url = f"{_api_base(sandbox=sandbox)}/v1/oauth2/token"
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    resp = requests.post(
        url,
        headers={"Authorization": f"Basic {basic}"},
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    if not resp.ok:
        logger.warning("PayPal token error: %s %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("Risposta PayPal senza access_token")
    return str(token)


def paypal_create_order(
    *,
    access_token: str,
    sandbox: bool,
    currency_code: str,
    value_str: str,
    description: str,
    custom_id: str,
) -> dict[str, Any]:
    url = f"{_api_base(sandbox=sandbox)}/v2/checkout/orders"
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": currency_code, "value": value_str},
                "description": description[:127],
                "custom_id": custom_id[:127],
            }
        ],
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=45,
    )
    if not resp.ok:
        logger.warning("PayPal create order: %s %s", resp.status_code, resp.text[:800])
        resp.raise_for_status()
    return resp.json()


def paypal_capture_order(*, access_token: str, sandbox: bool, order_id: str) -> dict[str, Any]:
    url = f"{_api_base(sandbox=sandbox)}/v2/checkout/orders/{order_id}/capture"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={},
        timeout=45,
    )
    if not resp.ok:
        logger.warning("PayPal capture: %s %s", resp.status_code, resp.text[:800])
        resp.raise_for_status()
    return resp.json()


def format_euro_amount(value: Decimal) -> str:
    q = value.quantize(Decimal("0.01"))
    return format(q, "f")
