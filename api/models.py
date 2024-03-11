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
    
    #     def sms_user(self,message):
    #     username = "emeden" 
    #     api_key = "REMOVED_SECRET"
    #     africastalking.initialize(username, api_key) 
    #     sms = africastalking.SMS
    #     sms.send(message, ["+" + str(self.phone)], sender_id="EMEDEN")

    #     #Add to database
    #     message_model = Message()
    #     message_model.profile = self
    #     message_model.message = message
    #     message_model.message_type = 'SMS'
    #     message_model.save()
    #     return 0

    # def email_user(self,message,subject="EMEDEN Kenya Farmers"):
    #     send_mail(
    #              subject,
    #              message,
    #             'info@emedenkenyafarmers.co.ke',
    #              [self.user.email],
    #              fail_silently=True,
    #              )
    #     #Add to database
    #     message_model = Message()
    #     message_model.profile = self
    #     message_model.message = message
    #     message_model.message_type = 'Email'
    #     message_model.save()
    #     return 0


class Artist(models.Model):
    profile = models.OneToOneField(
        Profile, default=None, on_delete=models.CASCADE, null=True)

    mpesa_number = models.IntegerField(null=True, blank=True)
    preferred_payout_method = models.CharField(choices=[('mpesa', 'mpesa')], default='mpesa', blank=True, null=True, max_length=10)
    revenue_earned = models.FloatField(blank=True, null=True)
    current_balance = models.FloatField(blank=True, null=True)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.profile.user


class Payout(models.Model):
    artist = models.ForeignKey(
        Artist, on_delete=models.SET_NULL, null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(blank=True, null=True, max_length=10)
    receipt_url = models.URLField(blank=True, null=True, max_length=100)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f'{self.date} {self.artist}'


class Player(models.Model):
    profile = models.OneToOneField(
        Profile, default=None, on_delete=models.CASCADE, null=True)

    calibration = models.FloatField(blank=True, null=True)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.profile.user


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
    artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, null=True, blank=True)
    genre = models.ForeignKey(
        Genre, on_delete=models.CASCADE, null=True, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True)
    tribe = models.ForeignKey(
        Tribe, on_delete=models.CASCADE, null=True, blank=True)

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


class PlayerSongInstance(models.Model):
    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, null=True, blank=True)
    
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True)
    
    date_first_played = models.DateTimeField(auto_now_add=True)
    date_last_played = models.DateTimeField(auto_now=True)
    high_score = models.IntegerField(blank=True, null=True)
    # no_of_plays = models.IntegerField(blank=True, null=True)
    maximum_progress = models.FloatField(blank=True, null=True)
    paid_for_flag = models.BooleanField(default=False, blank=True, null=True)
    favourited = models.BooleanField(default=False, blank=True, null=True)
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
