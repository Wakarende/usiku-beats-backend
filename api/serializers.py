from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
from .models import Profile

class SongSerializer(serializers.ModelSerializer):
    
	country_code = serializers.SerializerMethodField()
	country_name = serializers.SerializerMethodField()

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


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'
