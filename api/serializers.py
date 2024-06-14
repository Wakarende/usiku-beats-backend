from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
from .models import Profile

class SongSerializer(serializers.ModelSerializer):
    country_code = serializers.SerializerMethodField()
    country_name = serializers.SerializerMethodField()
    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_bio = serializers.CharField(source='artist.bio', read_only=True)
    artist_spotify_link = serializers.URLField(source='artist.spotify_link', read_only=True)
    artist_twitter_link = serializers.URLField(source='artist.twitter_link', read_only=True)
    artist_youtube_link = serializers.URLField(source='artist.youtube_link', read_only=True)
    artist_instagram_link = serializers.URLField(source='artist.instagram_link', read_only=True)
    artist_website_link = serializers.URLField(source='artist.website_link', read_only=True)

    class Meta:
        model = Song
        exclude = ('country', 'midi_url', 'mp3_url', 'mp3_clip_url', 'thumbnail_url', 'consumer_price_per_play', 'artist_revenue_per_play')

    def get_country_code(self, obj):
        return obj.country.code if obj.country else None

    def get_country_name(self, obj):
        return obj.country.name if obj.country else None
    
    def get_artist_name(self, obj):
        return obj.artist.name if object.artist else None


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password',)
        # fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'