"""
Utility functions for Admin Dashboard APIs.
- Google OAuth token verification
- Admin user lookup
- Audit logging helper
- RBAC permission definitions
"""
import requests as http_requests
from .models import AdminUser, AuditLog


def get_admin_user(request):
    """
    Extract the Google access token from the Authorization header,
    verify it with Google, and look up the admin user.

    Expected header: Authorization: Bearer <google_access_token>

    Returns AdminUser instance if valid, or None.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:].strip()
    if not token:
        return None

    # Verify the token with Google
    try:
        google_response = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )

        if google_response.status_code != 200:
            return None

        google_data = google_response.json()
    except Exception:
        return None

    email = google_data.get('email')
    if not email:
        return None

    # Look up the admin user
    try:
        admin = AdminUser.objects.get(google_email=email, status='active')
        return admin
    except AdminUser.DoesNotExist:
        return None


def log_audit(admin_email, action, entity_type, entity_id=None, changes=None, request=None):
    """
    Create an audit log entry.
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        admin_email=admin_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address,
    )


# RBAC Permission Definitions
ROLE_PERMISSIONS = {
    'content_editor': [
        'labels.view',
        'songs.view', 'songs.create', 'songs.edit',
        'artists.view', 'artists.create', 'artists.edit',
        'suggestions.view', 'suggestions.update_status',
    ],
    'product_manager': [
        'labels.view', 'labels.create', 'labels.edit',
        'songs.view', 'songs.create', 'songs.edit', 'songs.delete',
        'artists.view', 'artists.create', 'artists.edit', 'artists.delete',
        'users.view',
        'revenue.view',
        'business.view',
        'suggestions.view', 'suggestions.update_status', 'suggestions.ingest',
        'settings.view',
    ],
    'super_user': [
        'labels.view', 'labels.create', 'labels.edit', 'labels.delete',
        'songs.view', 'songs.create', 'songs.edit', 'songs.delete',
        'artists.view', 'artists.create', 'artists.edit', 'artists.delete',
        'users.view', 'users.freeze', 'users.kick', 'users.export',
        'revenue.view', 'revenue.export', 'revenue.create_payment', 'revenue.update_payment',
        'business.view', 'business.export',
        'suggestions.view', 'suggestions.update_status', 'suggestions.ingest',
        'settings.view', 'settings.create', 'settings.edit',
        'admin_users.view', 'admin_users.create', 'admin_users.edit', 'admin_users.delete',
        'audit_log.view',
    ],
}


def get_admin_permissions(role):
    """Return list of permission strings for a given admin role."""
    return ROLE_PERMISSIONS.get(role, [])
