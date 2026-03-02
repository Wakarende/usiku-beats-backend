import base64
import logging
import re

import requests as http_requests

from .constants import (
    XSOLLA_API_KEY,
    XSOLLA_ITEM_SKU,
    XSOLLA_MERCHANT_ID,
    XSOLLA_PROJECT_ID,
)
from .models import CountryPricing, GameSettings


logger = logging.getLogger(__name__)


def _build_auth_header():
    auth_string = f"{XSOLLA_MERCHANT_ID}:{XSOLLA_API_KEY}"
    auth_encoded = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    return f"Basic {auth_encoded}"


def _build_item_url(item_sku):
    return (
        f"https://store.xsolla.com/api/v2/project/{XSOLLA_PROJECT_ID}"
        f"/admin/items/virtual_items/sku/{item_sku}"
    )


def _get_bundle_usd_price():
    try:
        setting = GameSettings.objects.filter(
            key="price_per_bundle_usd",
            effective_to__isnull=True,
        ).latest("effective_from")
        return float(setting.value)
    except (GameSettings.DoesNotExist, TypeError, ValueError):
        return None
    except Exception as exc:
        logger.exception("Failed reading price_per_bundle_usd from GameSettings: %s", exc)
        return None


def get_xsolla_item(item_sku=XSOLLA_ITEM_SKU):
    url = _build_item_url(item_sku)
    headers = {
        "Authorization": _build_auth_header(),
        "Content-Type": "application/json",
    }

    try:
        response = http_requests.get(url, headers=headers, timeout=20)
    except Exception as exc:
        logger.exception("Xsolla item fetch failed for sku=%s: %s", item_sku, exc)
        return {"success": False, "error": str(exc), "stage": "get_item"}

    if not response.ok:
        logger.error(
            "Xsolla item fetch error for sku=%s status=%s body=%s",
            item_sku,
            response.status_code,
            response.text,
        )
        return {
            "success": False,
            "stage": "get_item",
            "status_code": response.status_code,
            "error": response.text,
        }

    try:
        item_json = response.json()
    except Exception as exc:
        logger.exception("Failed to decode Xsolla item JSON for sku=%s: %s", item_sku, exc)
        return {"success": False, "error": str(exc), "stage": "parse_item"}

    return {"success": True, "item": item_json}


def sync_prices_to_xsolla(item_sku=XSOLLA_ITEM_SKU):
    item_result = get_xsolla_item(item_sku=item_sku)
    if not item_result.get("success"):
        return item_result

    item_payload = item_result["item"]
    bundle_usd_price = _get_bundle_usd_price()
    existing_prices = item_payload.get("prices", [])
    if not isinstance(existing_prices, list):
        existing_prices = []

    default_prices = [
        price for price in existing_prices
        if isinstance(price, dict) and price.get("is_default") is True
    ]
    updated_default_prices = []
    default_usd_updated = False

    for price in default_prices:
        updated_price = dict(price)
        currency = (updated_price.get("currency") or "").upper()
        if bundle_usd_price is not None and (currency in ("", "USD")):
            updated_price["amount"] = bundle_usd_price
            if not updated_price.get("currency"):
                updated_price["currency"] = "USD"
            updated_price["is_default"] = True
            if "is_enabled" not in updated_price:
                updated_price["is_enabled"] = True
            default_usd_updated = True
        updated_default_prices.append(updated_price)

    if bundle_usd_price is not None and not default_usd_updated:
        updated_default_prices.append({
            "amount": bundle_usd_price,
            "currency": "USD",
            "is_default": True,
            "is_enabled": True,
        })
        default_usd_updated = True

    # Pre-fetch all rows and validate amounts once before the retry loop.
    valid_rows = []
    invalid_rows = []
    for row in CountryPricing.objects.filter(
        is_active=True,
        final_price__isnull=False,
    ).order_by("country_code"):
        try:
            amount = float(row.final_price)
            valid_rows.append((row, amount))
        except (TypeError, ValueError):
            invalid_rows.append({"country": row.country_code, "reason": "invalid_final_price"})

    headers = {
        "Authorization": _build_auth_header(),
        "Content-Type": "application/json",
    }
    url = _build_item_url(item_sku)

    # Retry loop: attempt the PUT with all currencies. If Xsolla returns
    # error 1014 for a specific currency (not configured at project level),
    # exclude that currency and retry. This allows all genuinely supported
    # currencies through without blocking them via a pre-filter.
    excluded_currencies = set()
    MAX_RETRIES = 15

    for attempt in range(MAX_RETRIES):
        synced_country_prices = []
        skipped_by_exclusion = []

        for row, amount in valid_rows:
            currency = (row.currency_code or "").upper()
            if currency in excluded_currencies:
                skipped_by_exclusion.append({
                    "country": row.country_code,
                    "reason": f"currency_rejected_by_xsolla: {currency}",
                })
                continue
            synced_country_prices.append({
                "amount": amount,
                "currency": currency,
                "country_iso": (row.country_code or "").upper(),
                "is_default": False,
                "is_enabled": True,
            })

        item_payload["prices"] = updated_default_prices + synced_country_prices

        try:
            put_response = http_requests.put(url, headers=headers, json=item_payload, timeout=20)
        except Exception as exc:
            logger.exception("Xsolla item update failed for sku=%s: %s", item_sku, exc)
            return {"success": False, "error": str(exc), "stage": "update_item"}

        if put_response.ok:
            skipped_rows = invalid_rows + skipped_by_exclusion
            logger.info(
                "Xsolla pricing sync success sku=%s synced=%s attempts=%s excluded=%s skipped=%s",
                item_sku,
                len(synced_country_prices),
                attempt + 1,
                list(excluded_currencies),
                skipped_rows,
            )
            return {
                "success": True,
                "sku": item_sku,
                "synced_prices": len(synced_country_prices),
                "default_prices_kept": len(updated_default_prices),
                "default_usd_updated": default_usd_updated,
                "excluded_currencies": list(excluded_currencies),
                "skipped_rows": skipped_rows,
            }

        # Check if Xsolla rejected a specific currency (error 1014).
        # If so, exclude it and retry rather than failing the whole sync.
        try:
            error_body = put_response.json()
        except Exception:
            error_body = {}

        error_code = error_body.get("errorCode")
        error_message = error_body.get("errorMessage", put_response.text)

        if error_code == 1014:
            match = re.search(r"currency with code\s*=\s*(\w+)", error_message, re.IGNORECASE)
            if match:
                bad_currency = match.group(1).upper()
                excluded_currencies.add(bad_currency)
                logger.warning(
                    "Xsolla rejected currency=%s (error 1014), excluding and retrying (attempt %s/%s)",
                    bad_currency, attempt + 1, MAX_RETRIES,
                )
                continue

        # Non-retryable error — return immediately.
        logger.error(
            "Xsolla item update error for sku=%s status=%s body=%s",
            item_sku,
            put_response.status_code,
            put_response.text,
        )
        return {
            "success": False,
            "stage": "update_item",
            "status_code": put_response.status_code,
            "error": put_response.text,
        }

    # Reached MAX_RETRIES — too many unsupported currencies.
    return {
        "success": False,
        "stage": "update_item",
        "error": f"Sync aborted after {MAX_RETRIES} attempts. Currencies rejected by Xsolla: {list(excluded_currencies)}",
        "excluded_currencies": list(excluded_currencies),
    }
