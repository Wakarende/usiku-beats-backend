"""
Admin Dashboard API Views.
Phase A: Labels, Admin Users, Game Settings, Audit Log, Auth

Authentication: Google OAuth token verified against api_admin_user table.
All endpoints require the admin to be active in the admin_user table.
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from decimal import Decimal

from .models import Label, AdminUser, GameSettings, AuditLog, CountryPricing
from .admin_serializers import (
    LabelSerializer, LabelCreateSerializer, LabelUpdateSerializer,
    AdminUserSerializer, AdminUserCreateSerializer, AdminUserUpdateSerializer,
    GameSettingsSerializer, GameSettingsCreateSerializer, GameSettingsUpdateSerializer,
    AuditLogSerializer,
    CountryPricingSerializer, CountryPricingUpdateSerializer,
)
from .admin_utils import get_admin_user, log_audit, get_admin_permissions


# ============================================================
# LABEL ENDPOINTS
# ============================================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def label_list(request):
    """GET /admin/labels/ - List all labels."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    labels = Label.objects.all().order_by('name')
    serializer = LabelSerializer(labels, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def label_create(request):
    """POST /admin/labels/ - Create a new label."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    serializer = LabelCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    label = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='label',
        entity_id=str(label.id),
        changes={'name': label.name, 'is_system': label.is_system},
        request=request,
    )

    return Response(LabelSerializer(label).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def label_detail(request, pk):
    """GET /admin/labels/<pk>/ - Get label detail with artist list."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    label = get_object_or_404(Label, pk=pk)
    data = LabelSerializer(label).data

    # Include the artists under this label
    from .models import Artist
    artists = Artist.objects.filter(label=label).values('id', 'name')
    data['artists'] = list(artists)

    return Response(data)


@api_view(['PUT', 'PATCH'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def label_update(request, pk):
    """PUT/PATCH /admin/labels/<pk>/ - Update a label."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    label = get_object_or_404(Label, pk=pk)
    old_data = {'name': label.name, 'is_system': label.is_system}

    serializer = LabelUpdateSerializer(label, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    label = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='label',
        entity_id=str(label.id),
        changes={'old': old_data, 'new': {'name': label.name, 'is_system': label.is_system}},
        request=request,
    )

    return Response(LabelSerializer(label).data)


@api_view(['DELETE'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def label_delete(request, pk):
    """DELETE /admin/labels/<pk>/ - Delete a label (reassign artists to Unknown)."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can delete labels'}, status=status.HTTP_403_FORBIDDEN)

    label = get_object_or_404(Label, pk=pk)

    if label.is_system:
        return Response({'error': 'Cannot delete system labels'}, status=status.HTTP_400_BAD_REQUEST)

    # Reassign artists to "Unknown" label
    from .models import Artist
    unknown_label = Label.objects.filter(name='Unknown').first()
    reassigned_count = 0
    if unknown_label:
        reassigned_count = Artist.objects.filter(label=label).update(label=unknown_label)

    label_name = label.name
    label_id = label.id
    label.delete()

    log_audit(
        admin_email=admin.google_email,
        action='delete',
        entity_type='label',
        entity_id=str(label_id),
        changes={'name': label_name, 'artists_reassigned': reassigned_count},
        request=request,
    )

    return Response({'message': f'Label "{label_name}" deleted. {reassigned_count} artists reassigned to Unknown.'})


# ============================================================
# ADMIN USER ENDPOINTS
# ============================================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def admin_user_list(request):
    """GET /admin/users/admins/ - List all admin users."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can manage admins'}, status=status.HTTP_403_FORBIDDEN)

    admins = AdminUser.objects.all().order_by('display_name')
    serializer = AdminUserSerializer(admins, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def admin_user_create(request):
    """POST /admin/users/admins/ - Create a new admin user."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can create admins'}, status=status.HTTP_403_FORBIDDEN)

    serializer = AdminUserCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_admin = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='admin_user',
        entity_id=str(new_admin.id),
        changes={'google_email': new_admin.google_email, 'role': new_admin.role},
        request=request,
    )

    return Response(AdminUserSerializer(new_admin).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def admin_user_update(request, pk):
    """PUT/PATCH /admin/users/admins/<pk>/ - Update an admin user."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can update admins'}, status=status.HTTP_403_FORBIDDEN)

    target = get_object_or_404(AdminUser, pk=pk)
    old_data = {'display_name': target.display_name, 'role': target.role, 'status': target.status}

    serializer = AdminUserUpdateSerializer(target, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    target = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='admin_user',
        entity_id=str(target.id),
        changes={'old': old_data, 'new': {'display_name': target.display_name, 'role': target.role, 'status': target.status}},
        request=request,
    )

    return Response(AdminUserSerializer(target).data)


@api_view(['DELETE'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def admin_user_delete(request, pk):
    """DELETE /admin/users/admins/<pk>/ - Delete an admin user."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can delete admins'}, status=status.HTTP_403_FORBIDDEN)

    target = get_object_or_404(AdminUser, pk=pk)

    # Prevent self-deletion
    if target.google_email == admin.google_email:
        return Response({'error': 'Cannot delete yourself'}, status=status.HTTP_400_BAD_REQUEST)

    email = target.google_email
    target_id = target.id
    target.delete()

    log_audit(
        admin_email=admin.google_email,
        action='delete',
        entity_type='admin_user',
        entity_id=str(target_id),
        changes={'google_email': email},
        request=request,
    )

    return Response({'message': f'Admin user {email} deleted.'})


# ============================================================
# GAME SETTINGS ENDPOINTS
# ============================================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def settings_list(request):
    """GET /admin/settings/ - List current (active) game settings."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    # Return only currently active settings (effective_to IS NULL)
    show_all = request.GET.get('all', 'false').lower() == 'true'

    if show_all:
        settings = GameSettings.objects.all()
    else:
        settings = GameSettings.objects.filter(effective_to__isnull=True)

    serializer = GameSettingsSerializer(settings, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def settings_create(request):
    """POST /admin/settings/ - Create a new setting (or new version of existing key)."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can create settings'}, status=status.HTTP_403_FORBIDDEN)

    serializer = GameSettingsCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # If a setting with the same key exists and has no effective_to, close it out
    key = serializer.validated_data['key']
    effective_from = serializer.validated_data.get('effective_from', timezone.now())
    existing = GameSettings.objects.filter(key=key, effective_to__isnull=True).first()
    if existing:
        existing.effective_to = effective_from
        existing.save()

    setting = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='game_settings',
        entity_id=str(setting.id),
        changes={'key': setting.key, 'value': setting.value},
        request=request,
    )

    return Response(GameSettingsSerializer(setting).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def settings_detail(request, pk):
    """GET /admin/settings/<pk>/ - Get a single setting."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    setting = get_object_or_404(GameSettings, pk=pk)
    return Response(GameSettingsSerializer(setting).data)


@api_view(['PUT', 'PATCH'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def settings_update(request, pk):
    """PUT/PATCH /admin/settings/<pk>/ - Update a setting."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can update settings'}, status=status.HTTP_403_FORBIDDEN)

    setting = get_object_or_404(GameSettings, pk=pk)
    old_value = setting.value

    serializer = GameSettingsUpdateSerializer(setting, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    setting = serializer.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='game_settings',
        entity_id=str(setting.id),
        changes={'key': setting.key, 'old_value': old_value, 'new_value': setting.value},
        request=request,
    )

    return Response(GameSettingsSerializer(setting).data)


# ============================================================
# COUNTRY PRICING ENDPOINTS
# ============================================================

def _get_usd_price():
    """Fetch the active price_per_bundle_usd setting from api_game_settings."""
    setting = GameSettings.objects.filter(
        key='price_per_bundle_usd', effective_to__isnull=True
    ).first()
    return Decimal(setting.value) if setting else None


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_list(request):
    """GET /admin/country-pricing/ - List all country pricing rows with computed fields."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    rows = CountryPricing.objects.all().order_by('country_name')
    usd_price = _get_usd_price()
    serializer = CountryPricingSerializer(rows, many=True, context={'usd_price': usd_price})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_detail(request, pk):
    """GET /admin/country-pricing/<pk>/ - Get a single country pricing row."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    row = get_object_or_404(CountryPricing, pk=pk)
    usd_price = _get_usd_price()
    serializer = CountryPricingSerializer(row, context={'usd_price': usd_price})
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_update(request, pk):
    """PUT/PATCH /admin/country-pricing/<pk>/update/ - Update a country's pricing fields."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    row = get_object_or_404(CountryPricing, pk=pk)
    old_data = {
        'final_price': str(row.final_price) if row.final_price is not None else None,
        'vat_rate': str(row.vat_rate),
        'notes': row.notes,
        'is_active': row.is_active,
    }

    serializer = CountryPricingUpdateSerializer(row, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    row = serializer.save(updated_by=admin)

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='country_pricing',
        entity_id=str(row.id),
        changes={
            'country_code': row.country_code,
            'old': old_data,
            'new': {
                'final_price': str(row.final_price) if row.final_price is not None else None,
                'vat_rate': str(row.vat_rate),
                'notes': row.notes,
                'is_active': row.is_active,
            },
        },
        request=request,
    )

    usd_price = _get_usd_price()
    return Response(CountryPricingSerializer(row, context={'usd_price': usd_price}).data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_bulk_update_rates(request):
    """
    POST /admin/country-pricing/bulk-update-rates/
    Bulk update exchange rates after a frontend fetch.
    Body: [{"country_code": "NG", "exchange_rate": 1612.5}, ...]
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    if not isinstance(payload, list):
        return Response(
            {'error': 'Expected a list of {country_code, exchange_rate} objects'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from decimal import InvalidOperation
    updated = []
    errors = []
    now = timezone.now()

    for item in payload:
        code = item.get('country_code')
        rate = item.get('exchange_rate')
        if not code or rate is None:
            errors.append({'country_code': code, 'error': 'country_code and exchange_rate are required'})
            continue
        try:
            rate_decimal = Decimal(str(rate))
        except InvalidOperation:
            errors.append({'country_code': code, 'error': 'Invalid exchange_rate value'})
            continue
        try:
            row = CountryPricing.objects.get(country_code=code)
            row.exchange_rate = rate_decimal
            row.exchange_rate_updated_at = now
            row.updated_by = admin
            row.save()
            updated.append(code)
        except CountryPricing.DoesNotExist:
            errors.append({'country_code': code, 'error': 'Country not found'})

    log_audit(
        admin_email=admin.google_email,
        action='bulk_update_rates',
        entity_type='country_pricing',
        changes={'countries_updated': len(updated), 'updated': updated, 'errors': errors},
        request=request,
    )

    return Response({'updated': updated, 'errors': errors})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def country_pricing_save_final_prices(request):
    """
    POST /admin/country-pricing/save-final-prices/
    Bulk save manually-entered final prices for multiple countries.
    Body: [{"country_code": "NG", "final_price": 175.0}, ...]
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    if not isinstance(payload, list):
        return Response(
            {'error': 'Expected a list of {country_code, final_price} objects'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from decimal import InvalidOperation
    updated = []
    errors = []

    for item in payload:
        code = item.get('country_code')
        price = item.get('final_price')
        if not code or price is None:
            errors.append({'country_code': code, 'error': 'country_code and final_price are required'})
            continue
        try:
            price_decimal = Decimal(str(price))
        except InvalidOperation:
            errors.append({'country_code': code, 'error': 'Invalid final_price value'})
            continue
        try:
            row = CountryPricing.objects.get(country_code=code)
            row.final_price = price_decimal
            row.updated_by = admin
            row.save()
            updated.append({'country_code': code, 'final_price': str(price_decimal)})
        except CountryPricing.DoesNotExist:
            errors.append({'country_code': code, 'error': 'Country not found'})

    log_audit(
        admin_email=admin.google_email,
        action='save_final_prices',
        entity_type='country_pricing',
        changes={'countries_updated': len(updated), 'prices': updated, 'errors': errors},
        request=request,
    )

    return Response({'updated': updated, 'errors': errors})


# ============================================================
# AUDIT LOG ENDPOINTS
# ============================================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def audit_log_list(request):
    """GET /admin/audit-log/ - List audit log entries with optional filters."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can view audit logs'}, status=status.HTTP_403_FORBIDDEN)

    logs = AuditLog.objects.all()

    # Optional filters
    entity_type = request.GET.get('entity_type')
    admin_email = request.GET.get('admin_email')
    action = request.GET.get('action')

    if entity_type:
        logs = logs.filter(entity_type=entity_type)
    if admin_email:
        logs = logs.filter(admin_email=admin_email)
    if action:
        logs = logs.filter(action=action)

    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    start = (page - 1) * page_size
    end = start + page_size

    total = logs.count()
    logs = logs[start:end]

    serializer = AuditLogSerializer(logs, many=True)
    return Response({
        'results': serializer.data,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def audit_log_detail(request, pk):
    """GET /admin/audit-log/<pk>/ - Get a single audit log entry."""
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can view audit logs'}, status=status.HTTP_403_FORBIDDEN)

    log = get_object_or_404(AuditLog, pk=pk)
    return Response(AuditLogSerializer(log).data)


# ============================================================
# AUTH ENDPOINT
# ============================================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def admin_auth_me(request):
    """
    GET /admin/auth/me/
    Verify the admin's Google token and return their profile + permissions.
    The frontend sends the Google OAuth access_token in the Authorization header.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    perms = get_admin_permissions(admin.role)

    return Response({
        'id': admin.id,
        'google_email': admin.google_email,
        'display_name': admin.display_name,
        'role': admin.role,
        'status': admin.status,
        'permissions': perms,
    })
