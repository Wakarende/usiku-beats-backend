from django.db import models
from django.contrib.auth.models import Permission, User


# ============================================================
# NEW TABLES (Admin Dashboard)
# ============================================================

class Label(models.Model):
    """Record labels for artist categorization."""
    name = models.CharField(max_length=100, unique=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_label'

    def __str__(self):
        return self.name


class AdminUser(models.Model):
    """Admin dashboard users authenticated via Google OAuth."""
    ROLE_CHOICES = (
        ('content_editor', 'Content Editor'),
        ('product_manager', 'Product Manager'),
        ('super_user', 'Super User'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    )

    google_email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='content_editor')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_admin_user'

    def __str__(self):
        return f'{self.display_name} ({self.google_email})'


class GameSettings(models.Model):
    """Versioned game economy settings with effective date ranges."""
    VALUE_TYPE_CHOICES = (
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('string', 'String'),
        ('boolean', 'Boolean'),
    )

    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default='string')
    description = models.TextField(blank=True, null=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'api_game_settings'
        unique_together = ('key', 'effective_from')
        ordering = ['key', '-effective_from']

    def __str__(self):
        return f'{self.key} = {self.value}'


class AuditLog(models.Model):
    """Immutable audit trail for all admin actions."""
    admin_email = models.EmailField()
    action = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_audit_log'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.admin_email} - {self.action} {self.entity_type} - {self.created_at}'


class CountryPricing(models.Model):
    """Per-country pricing configuration for bundle sales."""
    country_code = models.CharField(max_length=2, unique=True)
    country_name = models.CharField(max_length=50)
    currency_name = models.CharField(max_length=60)
    currency_code = models.CharField(max_length=3)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=4)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    exchange_rate_updated_at = models.DateTimeField(null=True, blank=True)
    final_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(default='', blank=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True, db_column='updated_by_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_country_pricing'
        managed = False  # Table was created directly via psycopg2; Django manages queries only
        ordering = ['country_name']

    def __str__(self):
        return f'{self.country_name} ({self.currency_code})'


class PaymentStatus(models.Model):
    """Track payment processing status for payee payouts."""
    STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    payee_type = models.CharField(max_length=20, blank=True, null=True)
    payee_id = models.BigIntegerField(blank=True, null=True)
    period_month = models.IntegerField(blank=True, null=True)
    period_year = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    invoice_date = models.DateField(blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True, db_column="updated_by_id")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_payment_status'
        ordering = ['-created_at']
        unique_together = [['payee_type', 'payee_id', 'period_month', 'period_year']]

    def __str__(self):
        return f'{self.payee_type}:{self.payee_id} - {self.period_year}/{self.period_month} - {self.status}'


class KickedPlayer(models.Model):
    """Record of players removed from the platform."""
    player = models.ForeignKey("Player", on_delete=models.CASCADE, related_name="kick_records", db_column="original_player_id")
    reason = models.TextField()
    kicked_by = models.ForeignKey("AdminUser", on_delete=models.SET_NULL, null=True, blank=True, db_column="kicked_by_id")
    kicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_kicked_players'
        ordering = ['-kicked_at']

    def __str__(self):
        return f'Player {self.player_id} kicked by {self.kicked_by.google_email if self.kicked_by else "unknown"}'


class ContentSuggestion(models.Model):
    """Content suggestions scraped from external charts/sources."""
    STATUS_CHOICES = (
        ('new', 'New'),
        ('approved', 'Approved'),
        ('dismissed', 'Dismissed'),
    )

    external_source = models.CharField(max_length=100, blank=True, null=True)
    external_id = models.CharField(max_length=200, blank=True, null=True)
    song_title = models.CharField(max_length=200, blank=True, null=True)
    artist_name = models.CharField(max_length=200, blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    chart_regions = models.JSONField(blank=True, null=True)
    peak_position = models.IntegerField(blank=True, null=True)
    current_popularity = models.IntegerField(blank=True, null=True)
    first_seen = models.DateTimeField(blank=True, null=True)
    weeks_trending = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    dismissed_reason = models.TextField(blank=True, null=True)
    acted_by = models.ForeignKey("AdminUser", on_delete=models.SET_NULL, null=True, blank=True, db_column="acted_by_id")
    acted_at = models.DateTimeField(blank=True, null=True)
    linked_song = models.ForeignKey("Song", on_delete=models.SET_NULL, null=True, blank=True, db_column="linked_song_id")
    data = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'api_content_suggestion'
        ordering = ['-first_seen']

    def __str__(self):
        return f'{self.song_title} by {self.artist_name} ({self.status})'


# ============================================================
# EXISTING TABLES (with new fields added)
# ============================================================

class Profile(models.Model):
    user = models.OneToOneField(
        User, default=None, on_delete=models.CASCADE, null=True)

    phone_number = models.IntegerField(null=True, blank=True)
    receive_notifications = models.BooleanField(default=True)
    recent_ip_address = models.GenericIPAddressField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    # New fields (admin dashboard)
    country = models.ForeignKey('Country', on_delete=models.SET_NULL, blank=True, null=True)
    country_source = models.CharField(max_length=30, blank=True, null=True, default='unknown')

    def __str__(self):
        return self.user.email



class Artist(models.Model):
    profile = models.OneToOneField(
        Profile, default=None, on_delete=models.CASCADE, blank=True, null=True)

    name = models.CharField(max_length=100, null=True, blank=True)
    mpesa_number = models.IntegerField(null=True, blank=True)
    preferred_payout_method = models.CharField(choices=[('mpesa', 'mpesa')], default='mpesa', blank=True, null=True, max_length=10)
    revenue_earned = models.FloatField(blank=True, null=True)
    current_balance = models.FloatField(blank=True, null=True)

    bio = models.TextField(null=True, blank=True)
    spotify_link = models.URLField(null=True, blank=True)
    twitter_link = models.URLField(null=True, blank=True)
    youtube_link = models.URLField(null=True, blank=True)
    instagram_link = models.URLField(null=True, blank=True)
    website_link = models.URLField(null=True, blank=True)

    data = models.JSONField(blank=True, null=True)

    # New fields (admin dashboard)
    label = models.ForeignKey(Label, on_delete=models.SET_NULL, blank=True, null=True, related_name='artists')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_artists')

    def __str__(self):
        return self.name


class Payout(models.Model):
    artist = models.ForeignKey(
        Artist, on_delete=models.SET_NULL, null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(blank=True, null=True, max_length=10)
    receipt_url = models.URLField(blank=True, null=True, max_length=100)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f'{self.date} {self.artist}'



class Genre(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Countries'
        
class Tribe(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Tribes'


class Song(models.Model):

    DIFFICULTY_CHOICES = (
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard")
    )

    artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, null=True, blank=True)
    genre = models.ForeignKey(
        Genre, on_delete=models.CASCADE, null=True, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True)
    tribe = models.ForeignKey(
        Tribe, on_delete=models.CASCADE, null=True, blank=True)
    
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    date_added = models.DateTimeField(auto_now_add=True)

    artist_name = models.CharField(max_length=100, blank=True, null=True)
    song_name = models.CharField(max_length=100, blank=True, null=True)

    midi_url = models.URLField(max_length=200, blank=True, null=True)
    midi_file =  models.FileField(blank=True, null=True)

    mp3_url = models.URLField(max_length=200, blank=True, null=True)
    mp3_file =  models.FileField(blank=True, null=True)

    mp3_clip_url = models.URLField(max_length=200, blank=True, null=True)
    mp3_clip_file = models.FileField(blank=True, null=True)

    thumbnail_url = models.URLField(max_length=200, blank=True, null=True)
    thumbnail_file = models.FileField(blank=True, null=True)

    status = models.CharField(choices=[('active', 'active'), ('inactive', 'inactive')], max_length=10, default='active')
    consumer_price_per_play = models.FloatField(blank=True, null=True)
    artist_revenue_per_play = models.FloatField(blank=True, null=True)
    # average_score = models.IntegerField(blank=True, null=True)

    platform = models.CharField(choices=[('usiku', 'usiku'), ('mdundo', 'mdundo')], max_length=10, default='usiku')
    promoted = models.BooleanField(default=False)
    data = models.JSONField(blank=True, null=True)

    # New fields (admin dashboard)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_songs')
    go_live_date = models.DateTimeField(blank=True, null=True)
    expiry_date = models.DateTimeField(blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    is_library = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.artist_name} - {self.song_name} - {self.id}'


class Player(models.Model):
    PLAYER_STATUS_CHOICES = (
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('kicked', 'Kicked'),
    )

    profile = models.OneToOneField(
        Profile, default=None, on_delete=models.CASCADE, null=True)

    calibration = models.FloatField(blank=True, null=True)

    level = models.IntegerField(default=1)
    total_discs = models.FloatField(default=0)
    total_gems = models.FloatField(default=0)
    total_stars = models.FloatField(default=0)

    data = models.JSONField(blank=True, null=True)

    # New field (admin dashboard)
    status = models.CharField(max_length=20, choices=PLAYER_STATUS_CHOICES, default='active')

    def __str__(self):
        return self.profile.user.email
    
    
class PlayerSongInstance(models.Model):
    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, null=True, blank=True)

    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True, related_name='player_song_instances')

    date_added = models.DateTimeField(blank=True, null=True)
    # date_last_played = models.DateTimeField(auto_now=True)
    high_score = models.BigIntegerField(default=0)

    no_of_plays = models.BigIntegerField(default=0)
    unlock_time = models.DateTimeField(blank=True, null=True)
    unlocked = models.BooleanField(default=False)
    unlock_start_time = models.DateTimeField(blank=True, null=True)
    unlock_duration_sec = models.FloatField(blank=True, null=True)
    unlock_completed_at = models.DateTimeField(blank=True, null=True)

    maximum_progress = models.FloatField(blank=True, null=True)
    paid_for_flag = models.BooleanField(default=False, blank=True, null=True)
    favourited = models.BooleanField(default=False)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f'{self.song} - {self.player}'
    
    class Meta:
        verbose_name_plural = 'Player Song Instances'

    def percentage_plays(self, percentage):
        # get % OF PLAYS THAT ENDED IN < 10% OF TRACK
        pass



class SongInstance(models.Model):
    player_song = models.ForeignKey(
        PlayerSongInstance, on_delete=models.CASCADE, null=True, blank=True)
    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, null=True, blank=True)
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(blank=True, null=True)
    progress = models.FloatField(blank=True, null=True)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f'{self.player_song} - {self.date}'

    class Meta:
        verbose_name_plural = 'Song Instances'

    def percentage_plays(self, percentage):
        # get % OF PLAYS THAT ENDED IN < 10% OF TRACK
        pass


class WebhookLog(models.Model):
    """Store all incoming webhook data for tracking purposes"""

    source = models.CharField(max_length=50)  # e.g., 'xsolla', 'stripe', etc.
    notification_type = models.CharField(max_length=100, blank=True, null=True)
    payload = models.JSONField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    headers = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.source} - {self.notification_type} - {self.created_at}'

    class Meta:
        verbose_name_plural = 'Webhook Logs'
        ordering = ['-created_at']


class XsollaTransaction(models.Model):
    """Track Xsolla webhook transactions for idempotency and auditing"""

    STATUS_CHOICES = (
        ('paid', 'Paid'),
        ('canceled', 'Canceled'),
    )

    order_id = models.IntegerField(unique=True)
    invoice_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.IntegerField(blank=True, null=True)

    player = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='xsolla_transactions')
    user_external_id = models.CharField(max_length=255)  # User email from Xsolla

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    notification_type = models.CharField(max_length=50)

    currency = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Track what was granted
    discs_granted = models.IntegerField(default=0)
    gems_granted = models.IntegerField(default=0)

    # Store the full webhook payload for reference
    webhook_payload = models.JSONField()

    is_sandbox = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order {self.order_id} - {self.status} - {self.user_external_id}'

    class Meta:
        verbose_name_plural = 'Xsolla Transactions'
        ordering = ['-created_at']
