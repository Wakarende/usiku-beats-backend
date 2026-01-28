from django.db import models
from django.contrib.auth.models import Permission, User


class Profile(models.Model):
    user = models.OneToOneField(
        User, default=None, on_delete=models.CASCADE, null=True)

    phone_number = models.IntegerField(null=True, blank=True)
    receive_notifications = models.BooleanField(default=True)
    recent_ip_address = models.GenericIPAddressField(blank=True, null=True)

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



    def __str__(self):
        return f'{self.artist_name} - {self.song_name} - {self.id}'


class Player(models.Model):
    profile = models.OneToOneField(
        Profile, default=None, on_delete=models.CASCADE, null=True)

    calibration = models.FloatField(blank=True, null=True)
    
    level = models.IntegerField(default=1)
    total_discs = models.FloatField(default=0)
    total_gems = models.FloatField(default=0)
    total_stars = models.FloatField(default=0)

    
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.profile.user.email
    
    
class PlayerSongInstance(models.Model):
    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, null=True, blank=True)
    
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True, related_name='player_song_instances')
    
    date_added = models.DateTimeField(auto_now_add=True)
    # date_last_played = models.DateTimeField(auto_now=True)
    high_score = models.BigIntegerField(default=0)
    
    no_of_plays = models.BigIntegerField(default=0)
    unlock_time = models.DateTimeField(blank=True, null=True)
    unlocked = models.BooleanField(default=False)
    
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
