"""
Serializers for the Admin Dashboard APIs.
Phase A: Labels, Admin Users, Game Settings, Audit Log, Auth
"""
from rest_framework import serializers
from .models import Label, AdminUser, GameSettings, AuditLog


# ============================================================
# LABEL SERIALIZERS
# ============================================================

class LabelSerializer(serializers.ModelSerializer):
    artist_count = serializers.SerializerMethodField()

    class Meta:
        model = Label
        fields = ['id', 'name', 'is_system', 'artist_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_artist_count(self, obj):
        return obj.artists.count()


class LabelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['name', 'is_system']


class LabelUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['name', 'is_system']
        extra_kwargs = {
            'name': {'required': False},
            'is_system': {'required': False},
        }


# ============================================================
# ADMIN USER SERIALIZERS
# ============================================================

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['id', 'google_email', 'display_name', 'role', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class AdminUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['google_email', 'display_name', 'role']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['display_name', 'role', 'status']
        extra_kwargs = {
            'display_name': {'required': False},
            'role': {'required': False},
            'status': {'required': False},
        }


# ============================================================
# GAME SETTINGS SERIALIZERS
# ============================================================

class GameSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSettings
        fields = ['id', 'key', 'value', 'value_type', 'description',
                  'effective_from', 'effective_to']
        read_only_fields = ['id']


class GameSettingsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSettings
        fields = ['key', 'value', 'value_type', 'description', 'effective_from']


class GameSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSettings
        fields = ['value', 'description', 'effective_to']
        extra_kwargs = {
            'value': {'required': False},
            'description': {'required': False},
            'effective_to': {'required': False},
        }


# ============================================================
# AUDIT LOG SERIALIZER
# ============================================================

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'admin_email', 'action', 'entity_type', 'entity_id',
                  'changes', 'ip_address', 'created_at']
        read_only_fields = ['id', 'created_at']


# ============================================================
# AUTH SERIALIZER
# ============================================================

class AdminMeSerializer(serializers.Serializer):
    """Response for /admin/auth/me/ - returns current admin user info."""
    id = serializers.IntegerField()
    google_email = serializers.EmailField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    permissions = serializers.ListField(child=serializers.CharField())
