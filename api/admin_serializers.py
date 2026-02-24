"""
Serializers for the Admin Dashboard APIs.
Phase A: Labels, Admin Users, Game Settings, Audit Log, Auth
"""
from decimal import Decimal
from rest_framework import serializers
from .models import Label, AdminUser, GameSettings, AuditLog, CountryPricing


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
# COUNTRY PRICING SERIALIZERS
# ============================================================

class CountryPricingSerializer(serializers.ModelSerializer):
    calculated_local_price = serializers.SerializerMethodField()
    total_with_vat = serializers.SerializerMethodField()

    class Meta:
        model = CountryPricing
        fields = [
            'id', 'country_code', 'country_name', 'currency_name', 'currency_code',
            'vat_rate', 'exchange_rate', 'exchange_rate_updated_at',
            'calculated_local_price', 'total_with_vat',
            'final_price', 'notes', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_calculated_local_price(self, obj):
        if obj.exchange_rate is None:
            return None
        usd_price = self.context.get('usd_price')
        if usd_price is None:
            return None
        return str(round(usd_price * obj.exchange_rate, 2))

    def get_total_with_vat(self, obj):
        if obj.exchange_rate is None:
            return None
        usd_price = self.context.get('usd_price')
        if usd_price is None:
            return None
        local_price = usd_price * obj.exchange_rate
        return str(round(local_price * (1 + obj.vat_rate), 2))


class CountryPricingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryPricing
        fields = ['final_price', 'vat_rate', 'notes', 'is_active']
        extra_kwargs = {
            'final_price': {'required': False},
            'vat_rate': {'required': False},
            'notes': {'required': False},
            'is_active': {'required': False},
        }


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
