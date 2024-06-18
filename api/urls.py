from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
	path('', views.apiOverview, name="api-overview"),
	path('song-list/', views.songList, name="song-list"),
    path('initial-song-list/', views.get_initial_songs, name="get-initial-songs"),

    path('mdundo-song-list/', views.mdundoSongList, name="song-list"),
	path('song-detail/<str:pk>/', views.songDetail, name="song-detail"),
 
 
    path('songs/artist_name/<str:artist_name>/', views.song_by_artist_name, name='song-by-artist-name'),
    path('songs/tribe/<str:tribe_name>/', views.song_by_tribe, name='song-by-tribe'),
    path('songs/country/<str:country_name>/', views.song_by_country, name='song-by-country'),
    path('songs/genre/<str:genre_name>/', views.song_by_genre, name='song-by-genre'),
    
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
        # Artist detail
    path('artist-detail/<int:pk>/', views.artist_detail, name='artist-detail'),

    
    path('player/gems/', views.update_gems, name="update-gems"),
    path('player/stars/', views.update_stars, name="update-stars"),
    path('player/discs/', views.update_discs, name="update-discs"),
    path('player/level/', views.update_level, name="update-level"),
    
    path('player/songs/', views.get_player_songs, name="get-player-songs"),
    path('player/songs/<int:pk>/', views.update_player_song_instance, name='update-player-song-instance'),



    
]
