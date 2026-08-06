"""
Phase A API Test Suite
Tests all Phase A admin endpoints against the live API.
Requires: requests (pip install requests)

Before running:
1. Deploy the code to the server
2. Ensure the admin dashboard APIs are accessible

Since we can't deploy yet, this script tests the code structure
by importing and checking the modules, and then tests against the
live database to verify the models work with existing data.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'usiku_beats_api.settings')

def test_imports():
    """Test that all modules import without errors."""
    print("=" * 60)
    print("  PHASE A: CODE STRUCTURE TESTS")
    print("=" * 60)

    errors = []

    # Test 1: Import models
    print("\n  [1] Importing models...", end=" ")
    try:
        from api.models import (
            Label, AdminUser, GameSettings, AuditLog,
            PaymentStatus, KickedPlayer, ContentSuggestion,
            Profile, Artist, Song, Player,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Models import: {e}")

    # Test 2: Import serializers
    print("  [2] Importing admin_serializers...", end=" ")
    try:
        from api.admin_serializers import (
            LabelSerializer, LabelCreateSerializer, LabelUpdateSerializer,
            AdminUserSerializer, AdminUserCreateSerializer, AdminUserUpdateSerializer,
            GameSettingsSerializer, GameSettingsCreateSerializer, GameSettingsUpdateSerializer,
            AuditLogSerializer, AdminMeSerializer,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Serializers import: {e}")

    # Test 3: Import views
    print("  [3] Importing admin_views...", end=" ")
    try:
        from api.admin_views import (
            label_list, label_create, label_detail, label_update, label_delete,
            admin_user_list, admin_user_create, admin_user_update, admin_user_delete,
            settings_list, settings_create, settings_detail, settings_update,
            audit_log_list, audit_log_detail,
            admin_auth_me,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Views import: {e}")

    # Test 4: Import utils
    print("  [4] Importing admin_utils...", end=" ")
    try:
        from api.admin_utils import (
            get_admin_user, log_audit, get_admin_permissions, ROLE_PERMISSIONS,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Utils import: {e}")

    # Test 5: Import URLs
    print("  [5] Importing admin_urls...", end=" ")
    try:
        from api.admin_urls import urlpatterns
        print(f"OK ({len(urlpatterns)} URL patterns)")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"URLs import: {e}")

    # Test 6: Check URL pattern count
    print("  [6] Verifying URL patterns...", end=" ")
    try:
        from api.admin_urls import urlpatterns
        expected_count = 16  # auth/me + 5 labels + 4 admin_users + 4 settings + 2 audit_log
        actual_count = len(urlpatterns)
        if actual_count == expected_count:
            print(f"OK ({actual_count} patterns)")
        else:
            print(f"WARNING: Expected {expected_count}, got {actual_count}")
            errors.append(f"URL count: expected {expected_count}, got {actual_count}")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"URL count check: {e}")

    # Test 7: RBAC permissions
    print("  [7] Verifying RBAC permissions...", end=" ")
    try:
        from api.admin_utils import ROLE_PERMISSIONS
        roles = ['content_editor', 'product_manager', 'super_user']
        for role in roles:
            if role not in ROLE_PERMISSIONS:
                errors.append(f"Missing role: {role}")
                print(f"FAILED: Missing role {role}")
                break
        else:
            ce_count = len(ROLE_PERMISSIONS['content_editor'])
            pm_count = len(ROLE_PERMISSIONS['product_manager'])
            su_count = len(ROLE_PERMISSIONS['super_user'])
            print(f"OK (CE:{ce_count}, PM:{pm_count}, SU:{su_count} permissions)")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"RBAC check: {e}")

    # Test 8: Check new model fields on existing models
    print("  [8] Verifying new fields on existing models...", end=" ")
    try:
        from api.models import Artist, Song, Player, Profile
        # Check Artist has label and created_by
        assert hasattr(Artist, 'label'), "Artist missing 'label' field"
        assert hasattr(Artist, 'created_by'), "Artist missing 'created_by' field"
        # Check Song has new fields
        assert hasattr(Song, 'created_by'), "Song missing 'created_by' field"
        assert hasattr(Song, 'go_live_date'), "Song missing 'go_live_date' field"
        assert hasattr(Song, 'expiry_date'), "Song missing 'expiry_date' field"
        assert hasattr(Song, 'language'), "Song missing 'language' field"
        # Check Profile has country
        assert hasattr(Profile, 'country'), "Profile missing 'country' field"
        assert hasattr(Profile, 'country_source'), "Profile missing 'country_source' field"
        # Check Player has status
        assert hasattr(Player, 'status'), "Player missing 'status' field"
        print("OK (9 new fields verified)")
    except AssertionError as e:
        print(f"FAILED: {e}")
        errors.append(f"New fields: {e}")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"New fields check: {e}")

    # Test 9: Migration file exists
    print("  [9] Verifying migration file...", end=" ")
    migration_path = os.path.join(os.path.dirname(__file__), 'api', 'migrations', '0030_admin_dashboard_models.py')
    if os.path.exists(migration_path):
        print("OK (0030_admin_dashboard_models.py)")
    else:
        print("FAILED: Migration file not found")
        errors.append("Migration file missing")

    # Summary
    print(f"\n{'=' * 60}")
    if not errors:
        print("  ALL PHASE A CODE STRUCTURE TESTS PASSED")
    else:
        print(f"  {len(errors)} TEST(S) FAILED:")
        for err in errors:
            print(f"    - {err}")
    print("=" * 60)

    return len(errors) == 0


def test_database_directly():
    """Test the database tables directly via psycopg2 to verify Phase A data."""
    import os
    import psycopg2

    DB_CONFIG = {
        'dbname': os.environ.get('DB_NAME', 'usiku_beats_database'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
    }

    print("\n" + "=" * 60)
    print("  PHASE A: DATABASE VERIFICATION")
    print("=" * 60)

    errors = []

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Test 1: Labels table
        print("\n  [1] api_label table...", end=" ")
        cur.execute("SELECT id, name, is_system FROM api_label ORDER BY id")
        labels = cur.fetchall()
        if len(labels) >= 3:
            print(f"OK ({len(labels)} rows)")
            for row in labels:
                print(f"      ID:{row[0]} | {row[1]} | system:{row[2]}")
        else:
            print(f"WARNING: Expected >= 3, got {len(labels)}")
            errors.append(f"Labels: expected >= 3, got {len(labels)}")

        # Test 2: Admin users table
        print("\n  [2] api_admin_user table...", end=" ")
        cur.execute("SELECT id, google_email, display_name, role, status FROM api_admin_user ORDER BY id")
        admins = cur.fetchall()
        if len(admins) >= 7:
            print(f"OK ({len(admins)} rows)")
            for row in admins:
                print(f"      ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
        else:
            print(f"WARNING: Expected >= 7, got {len(admins)}")
            errors.append(f"Admin users: expected >= 7, got {len(admins)}")

        # Test 3: Game settings table
        print("\n  [3] api_game_settings table...", end=" ")
        cur.execute("SELECT key, value, value_type FROM api_game_settings WHERE effective_to IS NULL ORDER BY key")
        settings = cur.fetchall()
        if len(settings) >= 7:
            print(f"OK ({len(settings)} active settings)")
            for row in settings:
                print(f"      {row[0]} = {row[1]} ({row[2]})")
        else:
            print(f"WARNING: Expected >= 7, got {len(settings)}")
            errors.append(f"Game settings: expected >= 7, got {len(settings)}")

        # Test 4: Audit log table exists
        print("\n  [4] api_audit_log table...", end=" ")
        cur.execute("SELECT COUNT(*) FROM api_audit_log")
        count = cur.fetchone()[0]
        print(f"OK ({count} entries)")

        # Test 5: Artist label assignments
        print("\n  [5] Artist label assignments...", end=" ")
        cur.execute("""
            SELECT l.name, COUNT(*) FROM api_artist a
            JOIN api_label l ON a.label_id = l.id
            GROUP BY l.name ORDER BY l.name
        """)
        assignments = cur.fetchall()
        print(f"OK")
        for row in assignments:
            print(f"      {row[0]}: {row[1]} artists")
        cur.execute("SELECT COUNT(*) FROM api_artist WHERE label_id IS NULL")
        null_count = cur.fetchone()[0]
        print(f"      Unassigned: {null_count}")
        if null_count > 0:
            errors.append(f"Unassigned artists: {null_count}")

        # Test 6: Player status field
        print("\n  [6] Player status field...", end=" ")
        cur.execute("SELECT status, COUNT(*) FROM api_player GROUP BY status")
        statuses = cur.fetchall()
        print(f"OK")
        for row in statuses:
            print(f"      {row[0]}: {row[1]} players")

        # Test 7: New columns on existing tables
        print("\n  [7] New columns verification...", end=" ")
        new_cols = [
            ('api_artist', 'label_id'),
            ('api_artist', 'created_by_id'),
            ('api_song', 'created_by_id'),
            ('api_song', 'go_live_date'),
            ('api_song', 'expiry_date'),
            ('api_song', 'language'),
            ('api_profile', 'country_id'),
            ('api_profile', 'country_source'),
            ('api_player', 'status'),
        ]
        all_exist = True
        for table, col in new_cols:
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, col))
            exists = cur.fetchone()[0] > 0
            if not exists:
                all_exist = False
                errors.append(f"Missing column: {table}.{col}")
        if all_exist:
            print(f"OK (all 9 columns exist)")
        else:
            print(f"FAILED")

        # Test 8: Existing API data integrity
        print("\n  [8] Existing data integrity...", end=" ")
        checks = {
            'api_artist': 101,
            'api_song': 163,
            'api_player': 4,
            'api_profile': 10,
        }
        all_ok = True
        for table, expected in checks.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            if actual != expected:
                all_ok = False
                errors.append(f"{table}: expected {expected}, got {actual}")
        if all_ok:
            print("OK (row counts match)")
        else:
            print("MISMATCH")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"\n  DATABASE ERROR: {e}")
        errors.append(f"Database connection: {e}")

    # Summary
    print(f"\n{'=' * 60}")
    if not errors:
        print("  ALL PHASE A DATABASE TESTS PASSED")
    else:
        print(f"  {len(errors)} TEST(S) FAILED:")
        for err in errors:
            print(f"    - {err}")
    print("=" * 60)

    return len(errors) == 0


if __name__ == '__main__':
    code_ok = test_imports()
    db_ok = test_database_directly()

    print(f"\n{'=' * 60}")
    if code_ok and db_ok:
        print("  PHASE A: ALL TESTS PASSED - READY TO PROCEED")
    else:
        print("  PHASE A: SOME TESTS FAILED - REVIEW ABOVE")
    print("=" * 60)

    sys.exit(0 if (code_ok and db_ok) else 1)
