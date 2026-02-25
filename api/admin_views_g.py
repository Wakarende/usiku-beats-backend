from decimal import Decimal, InvalidOperation
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import CountryPricing, GameSettings
from .admin_utils import get_admin_user, log_audit

WRITE_ROLES = ("super_user", "product_manager")


def _get_bundle_usd_price():
    try:
        setting = GameSettings.objects.filter(
            key="price_per_bundle_usd", effective_to__isnull=True
        ).latest("effective_from")
        return Decimal(setting.value)
    except Exception:
        return Decimal("0.10")


def _serialize(row, usd_price):
    if row.exchange_rate is not None:
        calc_local = usd_price * row.exchange_rate
        total_vat = calc_local * (1 + row.vat_rate)
    else:
        calc_local = None
        total_vat = None

    return {
        "id": row.id,
        "country_code": row.country_code,
        "country_name": row.country_name,
        "currency_name": row.currency_name,
        "currency_code": row.currency_code,
        "vat_rate": str(row.vat_rate),
        "exchange_rate": str(row.exchange_rate) if row.exchange_rate is not None else None,
        "exchange_rate_updated_at": row.exchange_rate_updated_at.isoformat() if row.exchange_rate_updated_at else None,
        "calculated_local_price": str(round(calc_local, 2)) if calc_local is not None else None,
        "total_with_vat": str(round(total_vat, 2)) if total_vat is not None else None,
        "final_price": str(row.final_price) if row.final_price is not None else None,
        "notes": row.notes or "",
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_list(request):
    admin = get_admin_user(request)
    if not admin:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    usd_price = _get_bundle_usd_price()
    rows = CountryPricing.objects.all()
    return Response([_serialize(r, usd_price) for r in rows])


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_detail(request, pk):
    admin = get_admin_user(request)
    if not admin:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    row = get_object_or_404(CountryPricing, pk=pk)
    usd_price = _get_bundle_usd_price()
    return Response(_serialize(row, usd_price))


@api_view(["PUT", "PATCH"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_update(request, pk):
    admin = get_admin_user(request)
    if not admin:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    if admin.role not in WRITE_ROLES:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    row = get_object_or_404(CountryPricing, pk=pk)
    data = request.data
    changes = {}

    if "final_price" in data:
        try:
            row.final_price = Decimal(str(data["final_price"]))
            changes["final_price"] = str(row.final_price)
        except InvalidOperation:
            return Response({"error": "Invalid final_price"}, status=status.HTTP_400_BAD_REQUEST)

    if "vat_rate" in data:
        try:
            row.vat_rate = Decimal(str(data["vat_rate"]))
            changes["vat_rate"] = str(row.vat_rate)
        except InvalidOperation:
            return Response({"error": "Invalid vat_rate"}, status=status.HTTP_400_BAD_REQUEST)

    if "notes" in data:
        row.notes = data["notes"]
        changes["notes"] = row.notes

    if "is_active" in data:
        row.is_active = bool(data["is_active"])
        changes["is_active"] = row.is_active

    row.updated_by = admin
    row.save()

    log_audit(
        admin_email=admin.google_email,
        action="update_country_pricing",
        entity_type="CountryPricing",
        entity_id=str(row.id),
        changes=changes,
        request=request,
    )

    usd_price = _get_bundle_usd_price()
    return Response(_serialize(row, usd_price))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_bulk_update_rates(request):
    admin = get_admin_user(request)
    if not admin:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    if admin.role not in WRITE_ROLES:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    if not isinstance(payload, list):
        return Response({"error": "Expected a list"}, status=status.HTTP_400_BAD_REQUEST)

    updated = 0
    errors = []
    now = timezone.now()

    for item in payload:
        code = item.get("country_code")
        rate = item.get("exchange_rate")
        if not code or rate is None:
            errors.append(f"Missing fields in item: {item}")
            continue
        try:
            row = CountryPricing.objects.get(country_code=code)
            row.exchange_rate = Decimal(str(rate))
            row.exchange_rate_updated_at = now
            row.updated_by = admin
            row.save()
            updated += 1
        except CountryPricing.DoesNotExist:
            errors.append(f"Unknown country_code: {code}")
        except (InvalidOperation, ValueError) as e:
            errors.append(f"{code}: invalid rate: {e}")

    log_audit(
        admin_email=admin.google_email,
        action="bulk_update_exchange_rates",
        entity_type="CountryPricing",
        entity_id=None,
        changes={"updated": updated, "errors": errors},
        request=request,
    )

    return Response({"updated": updated, "errors": errors})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_save_final_prices(request):
    admin = get_admin_user(request)
    if not admin:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    if admin.role not in WRITE_ROLES:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    if not isinstance(payload, list):
        return Response({"error": "Expected a list"}, status=status.HTTP_400_BAD_REQUEST)

    updated = 0
    errors = []

    for item in payload:
        code = item.get("country_code")
        price = item.get("final_price")
        if not code or price is None:
            errors.append(f"Missing fields in item: {item}")
            continue
        try:
            row = CountryPricing.objects.get(country_code=code)
            row.final_price = Decimal(str(price))
            row.updated_by = admin
            row.save()
            updated += 1
        except CountryPricing.DoesNotExist:
            errors.append(f"Unknown country_code: {code}")
        except (InvalidOperation, ValueError) as e:
            errors.append(f"{code}: invalid price: {e}")

    log_audit(
        admin_email=admin.google_email,
        action="bulk_save_final_prices",
        entity_type="CountryPricing",
        entity_id=None,
        changes={"updated": updated, "errors": errors},
        request=request,
    )

    return Response({"updated": updated, "errors": errors})
