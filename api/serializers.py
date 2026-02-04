from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
# from .models import Profile

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        exclude = ('mpesa_number','preferred_payout_method','revenue_earned','current_balance')


class SongSerializer(serializers.ModelSerializer):
    
    country_code = serializers.SerializerMethodField()
    country_name = serializers.SerializerMethodField()
    artist = ArtistSerializer(read_only=True)


    class Meta:
        model = Song
        exclude = ('country','midi_url','mp3_url','mp3_clip_url','thumbnail_url','consumer_price_per_play','artist_revenue_per_play',)
		# fields ='__all__'
  
    def get_country_code(self, obj):
		# Check if the song has a related country and return its code
        return obj.country.code if obj.country else None

    def get_country_name(self, obj):
		# Check if the song has a related country and return its code
        return obj.country.name if obj.country else None


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password',)
        # fields = '__all__'

class PlayerSongInstanceSerializer(serializers.ModelSerializer):
    song = SongSerializer(read_only=True)  # Assuming the related name is 'player'
    # song_id = serializers.PrimaryKeyRelatedField(source='song', read_only=True)
    
    class Meta:
        model = PlayerSongInstance
        fields = '__all__'
        # fields = ['song_id', 'date_added', 'high_score', 'no_of_plays', 'unlock_time', 'unlocked', 'maximum_progress', 'paid_for_flag', 'favourited', 'data']

        
        
class PlayerSerializer(serializers.ModelSerializer):
    player_song_instances = PlayerSongInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = Player
        fields = ['calibration', 'level', 'total_discs', 'total_gems', 'total_stars', 'data', 'player_song_instances']
        
        
        
class ProfileSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)  # Assuming the related name is 'player'
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = '__all__'  # Include all other fields from the profile plus the player


class PlayerSongInstanceSyncSerializer(serializers.Serializer):
    song_id = serializers.IntegerField()
    high_score = serializers.FloatField(default=0)
    no_of_plays = serializers.IntegerField(default=0)
    favourited = serializers.BooleanField(default=False)
    unlocked = serializers.BooleanField(default=False)
    unlock_time = serializers.DateTimeField(allow_null=True, required=False)
    unlock_start_time = serializers.DateTimeField(allow_null=True, required=False)
    unlock_duration_sec = serializers.FloatField(allow_null=True, required=False)
    unlock_completed_at = serializers.DateTimeField(allow_null=True, required=False)
    maximum_progress = serializers.FloatField(allow_null=True, required=False, default=0)
    paid_for_flag = serializers.BooleanField(default=False)
    date_added = serializers.DateTimeField(allow_null=True, required=False)


class PlayerDataSyncSerializer(serializers.Serializer):
    level = serializers.IntegerField(required=False)
    total_discs = serializers.FloatField(required=False)
    total_gems = serializers.FloatField(required=False)
    total_stars = serializers.FloatField(required=False)


class PlayerSyncSerializer(serializers.Serializer):
    player = PlayerDataSyncSerializer(required=False)
    player_song_instances = PlayerSongInstanceSyncSerializer(many=True, required=False)





