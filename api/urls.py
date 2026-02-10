from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
	path('', views.apiOverview, name="api-overview"),
	path('song-list/', views.songList, name="song-list"),
    path('initial-song-list/', views.get_initial_songs, name="get-initial-songs"),
    path('songs/', views.get_songs_by_id, name="get-songs-by-id"),


    path('mdundo-song-list/', views.mdundoSongList, name="song-list"),
	path('song-detail/<str:pk>/', views.songDetail, name="song-detail"),
 
 
    path('songs/artist_name/<str:artist_name>/', views.song_by_artist_name, name='song-by-artist-name'),
    path('songs/tribe/<str:tribe_name>/', views.song_by_tribe, name='song-by-tribe'),
    path('songs/country/<str:country_name>/', views.song_by_country, name='song-by-country'),
    path('songs/genre/<str:genre_name>/', views.song_by_genre, name='song-by-genre'),
    
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('google-login/', views.google_login, name='google-login'),
    path('version/', views.get_version, name='get_version'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
        # Artist detail
    path('artist-detail/<int:pk>/', views.artist_detail, name='artist-detail'),

    
    path('player/sync/', views.sync_player_data, name="sync-player-data"),

    path('player/songs/', views.get_player_songs, name="get-player-songs"),
    path('player/songs/<int:pk>/', views.update_player_song_instance, name='update-player-song-instance'),


    path('analytics/', views.log_analytics, name='log_analytics'),

    # Xsolla
    path('webhooks/xsolla/', views.xsolla_webhook, name='xsolla-webhook'),
    path('payment/create-token/', views.create_xsolla_payment_token, name='create-xsolla-payment-token'),
]
