"""
URL patterns for Admin Dashboard APIs.
All endpoints are prefixed with /admin-api/ (configured in usiku_beats_api/urls.py).

Total: 55 endpoints across 6 phases + country pricing.
"""
from django.urls import path
from . import admin_views
from . import admin_views_b
from . import admin_views_c
from . import admin_views_d
from . import admin_views_e
from . import admin_views_f

urlpatterns = [
    # ========== Phase A: Foundation (16 endpoints) ==========

    # Auth
    path('auth/me/', admin_views.admin_auth_me, name='admin-auth-me'),

    # Labels CRUD
    path('labels/', admin_views.label_list, name='admin-label-list'),
    path('labels/create/', admin_views.label_create, name='admin-label-create'),
    path('labels/<int:pk>/', admin_views.label_detail, name='admin-label-detail'),
    path('labels/<int:pk>/update/', admin_views.label_update, name='admin-label-update'),
    path('labels/<int:pk>/delete/', admin_views.label_delete, name='admin-label-delete'),

    # Admin Users CRUD
    path('users/admins/', admin_views.admin_user_list, name='admin-user-list'),
    path('users/admins/create/', admin_views.admin_user_create, name='admin-user-create'),
    path('users/admins/<int:pk>/update/', admin_views.admin_user_update, name='admin-user-update'),
    path('users/admins/<int:pk>/delete/', admin_views.admin_user_delete, name='admin-user-delete'),

    # Game Settings CRUD
    path('settings/', admin_views.settings_list, name='admin-settings-list'),
    path('settings/create/', admin_views.settings_create, name='admin-settings-create'),
    path('settings/<int:pk>/', admin_views.settings_detail, name='admin-settings-detail'),
    path('settings/<int:pk>/update/', admin_views.settings_update, name='admin-settings-update'),

    # Audit Log (read-only)
    path('audit-log/', admin_views.audit_log_list, name='admin-audit-log-list'),
    path('audit-log/<int:pk>/', admin_views.audit_log_detail, name='admin-audit-log-detail'),

    # Country Pricing
    path('country-pricing/', admin_views.country_pricing_list, name='admin-country-pricing-list'),
    path('country-pricing/bulk-update-rates/', admin_views.country_pricing_bulk_update_rates, name='admin-country-pricing-bulk-rates'),
    path('country-pricing/save-final-prices/', admin_views.country_pricing_save_final_prices, name='admin-country-pricing-save-prices'),
    path('country-pricing/<int:pk>/', admin_views.country_pricing_detail, name='admin-country-pricing-detail'),
    path('country-pricing/<int:pk>/update/', admin_views.country_pricing_update, name='admin-country-pricing-update'),

    # ========== Phase B: User Management (6 endpoints) ==========

    path('users/', admin_views_b.user_list, name='admin-user-player-list'),
    path('users/export/', admin_views_b.user_export, name='admin-user-export'),
    path('users/<int:pk>/', admin_views_b.user_detail, name='admin-user-detail'),
    path('users/<int:pk>/freeze/', admin_views_b.user_freeze, name='admin-user-freeze'),
    path('users/<int:pk>/unfreeze/', admin_views_b.user_unfreeze, name='admin-user-unfreeze'),
    path('users/<int:pk>/kick/', admin_views_b.user_kick, name='admin-user-kick'),

    # ========== Phase C: Content Enhancement (10 endpoints) ==========

    # Songs CRUD
    path('songs/', admin_views_c.song_list, name='admin-song-list'),
    path('songs/create/', admin_views_c.song_create, name='admin-song-create'),
    path('songs/<int:pk>/', admin_views_c.song_detail, name='admin-song-detail'),
    path('songs/<int:pk>/update/', admin_views_c.song_update, name='admin-song-update'),
    path('songs/<int:pk>/delete/', admin_views_c.song_delete, name='admin-song-delete'),

    # Artists CRUD
    path('artists/', admin_views_c.artist_list, name='admin-artist-list'),
    path('artists/create/', admin_views_c.artist_create, name='admin-artist-create'),
    path('artists/<int:pk>/', admin_views_c.artist_detail_admin, name='admin-artist-detail'),
    path('artists/<int:pk>/update/', admin_views_c.artist_update, name='admin-artist-update'),
    path('artists/<int:pk>/delete/', admin_views_c.artist_delete, name='admin-artist-delete'),

    # ========== Phase D: Revenue Dashboard (7 endpoints) ==========

    path('revenue/summary/', admin_views_d.revenue_summary, name='admin-revenue-summary'),
    path('revenue/payees/', admin_views_d.revenue_payee_list, name='admin-revenue-payee-list'),
    path('revenue/payees/<int:pk>/', admin_views_d.revenue_payee_detail, name='admin-revenue-payee-detail'),
    path('revenue/payments/', admin_views_d.payment_status_list, name='admin-payment-list'),
    path('revenue/payments/create/', admin_views_d.payment_status_create, name='admin-payment-create'),
    path('revenue/payments/<int:pk>/update/', admin_views_d.payment_status_update, name='admin-payment-update'),
    path('revenue/export/', admin_views_d.revenue_export, name='admin-revenue-export'),

    # ========== Phase E: Business Dashboard Analytics (6 endpoints) ==========

    path('business/overview/', admin_views_e.business_overview, name='admin-business-overview'),
    path('business/users/', admin_views_e.business_users, name='admin-business-users'),
    path('business/content/', admin_views_e.business_content, name='admin-business-content'),
    path('business/engagement/', admin_views_e.business_engagement, name='admin-business-engagement'),
    path('business/revenue/', admin_views_e.business_revenue_analytics, name='admin-business-revenue'),
    path('business/geography/', admin_views_e.business_geography, name='admin-business-geography'),

    # ========== Phase F: Content Suggestions (4 endpoints) ==========

    path('suggestions/', admin_views_f.suggestion_list, name='admin-suggestion-list'),
    path('suggestions/summary/', admin_views_f.suggestion_summary, name='admin-suggestion-summary'),
    path('suggestions/<int:pk>/status/', admin_views_f.suggestion_update_status, name='admin-suggestion-status'),
    path('suggestions/ingest/', admin_views_f.suggestion_ingest, name='admin-suggestion-ingest'),
]
