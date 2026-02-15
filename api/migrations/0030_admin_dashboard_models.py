"""
Migration for Admin Dashboard models and fields.

NOTE: The database tables and columns were already created via raw SQL
(execute_db_changes.py and execute_phases_2_4.py) before this migration
was written. On the live server, run: python manage.py migrate --fake api 0030
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0029_webhooklog'),
    ]

    operations = [
        # ============================================================
        # NEW TABLES
        # ============================================================

        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('is_system', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'api_label',
            },
        ),

        migrations.CreateModel(
            name='AdminUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_email', models.EmailField(max_length=254, unique=True)),
                ('display_name', models.CharField(max_length=100)),
                ('role', models.CharField(choices=[('content_editor', 'Content Editor'), ('product_manager', 'Product Manager'), ('super_user', 'Super User')], default='content_editor', max_length=20)),
                ('status', models.CharField(choices=[('active', 'Active'), ('suspended', 'Suspended')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'api_admin_user',
            },
        ),

        migrations.CreateModel(
            name='GameSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100)),
                ('value', models.CharField(max_length=255)),
                ('value_type', models.CharField(choices=[('integer', 'Integer'), ('decimal', 'Decimal'), ('string', 'String'), ('boolean', 'Boolean')], default='string', max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('effective_from', models.DateTimeField()),
                ('effective_to', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'api_game_settings',
                'ordering': ['key', '-effective_from'],
                'unique_together': {('key', 'effective_from')},
            },
        ),

        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('admin_email', models.EmailField(max_length=254)),
                ('action', models.CharField(max_length=50)),
                ('entity_type', models.CharField(max_length=50)),
                ('entity_id', models.CharField(blank=True, max_length=50, null=True)),
                ('changes', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'api_audit_log',
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='PaymentStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('initiated_by', models.EmailField(blank=True, max_length=254, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_statuses', to='api.artist')),
            ],
            options={
                'db_table': 'api_payment_status',
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='KickedPlayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField()),
                ('kicked_by', models.EmailField(max_length=254)),
                ('kicked_at', models.DateTimeField(auto_now_add=True)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kick_records', to='api.player')),
            ],
            options={
                'db_table': 'api_kicked_players',
                'ordering': ['-kicked_at'],
            },
        ),

        migrations.CreateModel(
            name='ContentSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suggestion_type', models.CharField(choices=[('song', 'Song'), ('artist', 'Artist'), ('genre', 'Genre')], max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('detail', models.JSONField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('reviewed_by', models.EmailField(blank=True, max_length=254, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'api_content_suggestion',
                'ordering': ['-created_at'],
            },
        ),

        # ============================================================
        # NEW FIELDS ON EXISTING TABLES
        # ============================================================

        # Artist.label_id -> Label
        migrations.AddField(
            model_name='artist',
            name='label',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='artists', to='api.label'),
        ),

        # Artist.created_by_id -> auth_user
        migrations.AddField(
            model_name='artist',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_artists', to=settings.AUTH_USER_MODEL),
        ),

        # Song.created_by_id -> auth_user
        migrations.AddField(
            model_name='song',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_songs', to=settings.AUTH_USER_MODEL),
        ),

        # Song.go_live_date
        migrations.AddField(
            model_name='song',
            name='go_live_date',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Song.expiry_date
        migrations.AddField(
            model_name='song',
            name='expiry_date',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Song.language
        migrations.AddField(
            model_name='song',
            name='language',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),

        # Profile.country_id -> Country
        migrations.AddField(
            model_name='profile',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.country'),
        ),

        # Profile.country_source
        migrations.AddField(
            model_name='profile',
            name='country_source',
            field=models.CharField(blank=True, default='unknown', max_length=30, null=True),
        ),

        # Player.status
        migrations.AddField(
            model_name='player',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('frozen', 'Frozen'), ('kicked', 'Kicked')], default='active', max_length=20),
        ),
    ]
