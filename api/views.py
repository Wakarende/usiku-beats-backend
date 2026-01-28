from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import status, permissions, views
from rest_framework.response import Response
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.core.paginator import Paginator
import random
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .scripts import *
from django.contrib.auth import login as auth_login
from django.utils import timezone

@api_view(['GET'])
def apiOverview(request):
    api_urls = {
        'usiku-beats-api': 200
    }

    return Response(api_urls)

# @api_view(['GET'])
# def songList(request):
# 	start = int(request.GET.get('start', 0))
# 	limit = int(request.GET.get('limit', 5))
# 	songs = Song.objects.all()[start:start+limit]
# 	serializer = SongSerializer(songs, many=True,  context={'request': request})

# 	return Response(serializer.data)


# @api_view(['GET'])
# def songList(request):
#     start = int(request.GET.get('start', 0))
#     limit = int(request.GET.get('limit', 5))

#     # Determine the total count of songs excluding the ones from "mdundo"
#     total_songs = Song.objects.exclude(platform='mdundo').count()

#     # Ensure we don't exceed the bounds
#     start = min(start, total_songs - limit)

#     # Fetch a random set of songs excluding the ones from "mdundo"
#     songs = Song.objects.exclude(platform='mdundo')[start:start+limit]

#     serializer = SongSerializer(songs, many=True, context={'request': request})
#     return Response(serializer.data)



@api_view(['GET'])
@authentication_classes([JWTAuthentication])
# @permission_classes([permissions.IsAuthenticated])
def songList(request):
    
    if request.user.is_authenticated:
        print("user is authenticated")
        pass
        
        
    
    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 5))

    # Check if we have a shuffled list of song IDs in the session
    if 'shuffled_song_ids' not in request.session:
        # Fetch all song IDs excluding the ones from "mdundo"
        song_ids = list(Song.objects.exclude(platform='mdundo').values_list('id', flat=True))
        # Shuffle the list of song IDs
        random.shuffle(song_ids)
        # Store the shuffled list in the session
        request.session['shuffled_song_ids'] = song_ids
    else:
        # Retrieve the shuffled list from the session
        song_ids = request.session['shuffled_song_ids']
    
    # Use Django's Paginator to handle slicing the list based on start and limit
    paginator = Paginator(song_ids, limit)
    current_page_song_ids = paginator.get_page(start // limit + 1).object_list

    # Fetch the song details for the current page's song IDs
    songs = Song.objects.filter(id__in=current_page_song_ids)

    # data = {}
    # data['user'] = UserSerializer(request.user).data
    # data['songs'] = SongSerializer(songs, many=True, context={'request': request}).data
    # Serialize and return the song data
    serializer = SongSerializer(songs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def mdundoSongList(request):
    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 5))

    # Determine the total count of songs for the "mdundo" platform
    total_songs = Song.objects.filter(platform='mdundo').count()

    # Ensure we don't exceed the bounds
    start = min(start, total_songs - limit)

    # Fetch a random set of songs for the "mdundo" platform
    songs = Song.objects.filter(platform='mdundo').order_by('?')[start:start+limit]

    serializer = SongSerializer(songs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
# @permission_classes([permissions.IsAuthenticated])
def songDetail(request, pk):
    
    if request.user.is_authenticated:
        print("User is authenticated")
        pass
    
    song = Song.objects.get(id=pk)
    serializer = SongSerializer(song, many=False, context={'request': request})

    return Response(serializer.data)


@api_view(['GET'])
def song_by_artist_name(request, artist_name):
    songs = Song.objects.filter(artist_name=artist_name)[:10]
    serializer = SongSerializer(songs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def song_by_tribe(request, tribe_name):
    tribe = get_object_or_404(Tribe, name=tribe_name)
    songs = Song.objects.filter(tribe=tribe)[:10]
    serializer = SongSerializer(songs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def song_by_country(request, country_name):
    country = get_object_or_404(Country, name=country_name)
    songs = Song.objects.filter(country=country)[:10]
    serializer = SongSerializer(songs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def song_by_genre(request, genre_name):
    genre = get_object_or_404(Genre, name=genre_name)
    songs = Song.objects.filter(genre=genre)[:10]
    serializer = SongSerializer(songs, many=True)
    return Response(serializer.data)


# @csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup(request):
    email = request.data.get('email')
    password = request.data.get('password')


    ip_address = get_ip_address_from_request(request)

    if not password or not email:
        return Response({'error': 'All fields are required'}, status=status.HTTP_200_OK)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'User with this email already exists'}, status=status.HTTP_200_OK)

    username = generate_unique_username(email)
    user = User.objects.create_user(
        username=username, password=password, email=email)
    profile = Profile.objects.create(user=user, recent_ip_address=ip_address)
    player = Player.object.create(profile=profile)


    # auth_login(request._request, user)
    refresh = RefreshToken.for_user(user)


    data = {}
    data['profile'] = ProfileSerializer(profile).data


    return Response({
        'message': 'User created successfully',
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,

    }, status=status.HTTP_201_CREATED)


# @csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'Both email and password are required'}, status=status.HTTP_200_OK)

    user = User.objects.filter(email=email).first()

    if not user or not user.check_password(password):
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_200_OK)

    # auth_login(request._request, user)
    profile = Profile.objects.get(user=user)
    refresh = RefreshToken.for_user(user)



    data = {}
    data['profile'] = ProfileSerializer(profile).data

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,
    })



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_discs(request):
    
    player = get_object_or_404(Player, profile=request.user.profile)
    try:
        resource_to_add = float(request.data.get('discs', 0))
                
        new_total_resource = player.total_discs + resource_to_add
        if new_total_resource < 0:
            return Response({'error': 'Resource count cannot be less than 0'}, status=status.HTTP_400_BAD_REQUEST)

        player.total_discs = new_total_resource
        player.save()
        serializer = PlayerSerializer(player)
        return Response(serializer.data)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_stars(request):
    
    player = get_object_or_404(Player, profile=request.user.profile)
    try:
        resource_to_add = float(request.data.get('stars', 0))
                
        new_total_resource = player.total_stars + resource_to_add
        if new_total_resource < 0:
            return Response({'error': 'Resource count cannot be less than 0'}, status=status.HTTP_400_BAD_REQUEST)

        player.total_stars = new_total_resource
        player.save()
        serializer = PlayerSerializer(player)
        return Response(serializer.data)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_gems(request):
    
    player = get_object_or_404(Player, profile=request.user.profile)
    try:
        resource_to_add = float(request.data.get('gems', 0))
                
        new_total_resource = player.total_gems + resource_to_add
        if new_total_resource < 0:
            return Response({'error': 'Resource count cannot be less than 0'}, status=status.HTTP_400_BAD_REQUEST)

        player.total_gems = new_total_resource
        player.save()
        serializer = PlayerSerializer(player)
        return Response(serializer.data)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_level(request):

    player = get_object_or_404(Player, profile=request.user.profile)
    try:
        resource_to_add = float(request.data.get('level', 1))
                
        new_total_resource = player.level + resource_to_add
        if new_total_resource < 1:
            return Response({'error': 'Resource count cannot be less than 1'}, status=status.HTTP_400_BAD_REQUEST)

        player.level = new_total_resource
        player.save()
        serializer = PlayerSerializer(player)
        return Response(serializer.data)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_player_songs(request):

    player = get_object_or_404(Player, profile=request.user.profile)
    instances = PlayerSongInstance.objects.filter(player=player)
    
    data = PlayerSongInstanceSerializer(instances, many=True).data
    return Response(data, status=status.HTTP_200_OK)


    
@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_player_song_instance(request, pk):
    player_song_instance = get_object_or_404(PlayerSongInstance, pk=pk)
    
    # Check if the user is authorized to update this instance
    if player_song_instance.player.profile.user != request.user:
        return Response({'error': 'You do not have permission to update this song instance.'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = PlayerSongInstanceSerializer(player_song_instance, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
@api_view(['GET'])
def get_initial_songs(request):
    ids = request.GET.getlist('ids')  # Retrieve list of IDs from the query parameters
    if ids:
        songs = Song.objects.filter(id__in=ids)  # Query your model using the list of IDs
        
        # Create PlayerSongInstance objects with default values
        player_song_instances = []
        
        for song in songs:
            song_data = SongSerializer(song, context={'request': request}).data  # Serialize Song object
            player_song_instance = {
                'song': song_data,
                'high_score': 0,
                'no_of_plays': 0,
                'date_added': timezone.now(),
                'unlock_time': None,
                'unlocked': True,
                'maximum_progress': 0.0,
                'paid_for_flag': False,
                'favourited': False,
                'data': {}
            }
            player_song_instances.append(player_song_instance)

        # Serialize the PlayerSongInstance objects
        return Response(player_song_instances, status=status.HTTP_200_OK)
    
    return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_songs_by_id(request):
    ids = request.GET.getlist('ids')  # Retrieve list of IDs from the query parameters

    if not ids:
        return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

    songs = Song.objects.filter(id__in=ids)  # Query your model using the list of IDs
    song_data = SongSerializer(songs, many=True, context={'request': request}).data  # Serialize Song object
    return Response(song_data, status=status.HTTP_200_OK)

      



@api_view(['GET'])
def artist_detail(request, pk):
    
    artist = get_object_or_404(Artist, pk=pk)
    serializer = ArtistSerializer(artist, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_version(request):
    """
    Return the current app version for client version checking
    """
    version_data = {
        'version': '0.2.9',  # Make sure to update this when releasing new versions
        'required': True,     # Optional: set to True if update is mandatory
        'message': 'New features and bug fixes available!'  # Optional: message to show users
    }
    
    return Response(version_data, status=status.HTTP_200_OK)


# @api_view(['POST'])
# @permission_classes([permissions.AllowAny])
# def log_analytics(request):
#     import csv
#     import os
#     from datetime import datetime
#     from django.conf import settings
    
#     # Get parameters from POST request
#     session_id = request.data.get('sessionId', '')
#     event_id = request.data.get('eventId', '')
    
#     # Generate timestamp
#     timestamp = datetime.now().isoformat()
    
#     # Create analytics directory in media root or use a temp directory
#     try:
#         # Option 1: Use Django's MEDIA_ROOT (recommended)
#         if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
#             analytics_dir = os.path.join(settings.MEDIA_ROOT, 'analytics')
#         else:
#             # Option 2: Use system temp directory as fallback
#             import tempfile
#             analytics_dir = os.path.join(tempfile.gettempdir(), 'django_analytics')
        
#         # Create directory if it doesn't exist
#         os.makedirs(analytics_dir, exist_ok=True)
        
#         # Path to analytics CSV file
#         csv_file_path = os.path.join(analytics_dir, 'analytics.csv')
        
#     except Exception as e:
#         return Response({
#             'error': 'Failed to create analytics directory',
#             'details': str(e)
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
#     # Check if file exists to determine if we need to write headers
#     file_exists = os.path.isfile(csv_file_path)
    
#     try:
#         # Open file in append mode
#         with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
#             fieldnames = ['Timestamp', 'sessionId', 'eventId']
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
#             # Write header if file is new
#             if not file_exists:
#                 writer.writeheader()
            
#             # Write the data row
#             writer.writerow({
#                 'Timestamp': timestamp,
#                 'sessionId': session_id,
#                 'eventId': event_id
#             })
        
#         return Response({
#             'message': 'Analytics data logged successfully',
#             'timestamp': timestamp,
#             'file_path': csv_file_path  # For debugging - remove in production
#         }, status=status.HTTP_200_OK)
        
#     except Exception as e:
#         return Response({
#             'error': 'Failed to log analytics data',
#             'details': str(e)
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
#     # Get parameters from POST request
#     session_id = request.data.get('sessionId', '')
#     event_id = request.data.get('eventId', '')
    
#     # Generate timestamp
#     timestamp = datetime.now().isoformat()
    
#     # Path to analytics CSV file
#     csv_file_path = 'analytics.csv'
    
#     # Check if file exists to determine if we need to write headers
#     file_exists = os.path.isfile(csv_file_path)
    
#     try:
#         # Open file in append mode
#         with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
#             fieldnames = ['Timestamp', 'sessionId', 'eventId']
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
#             # Write header if file is new
#             if not file_exists:
#                 writer.writeheader()
            
#             # Write the data row
#             writer.writerow({
#                 'Timestamp': timestamp,
#                 'sessionId': session_id,
#                 'eventId': event_id
#             })
        
#         return Response({
#             'message': 'Analytics data logged successfully',
#             'timestamp': timestamp
#         }, status=status.HTTP_200_OK)
        
#     except Exception as e:
#         return Response({
#             'error': 'Failed to log analytics data',
#             'details': str(e)
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def log_analytics(request):
    import csv
    import os
    from datetime import datetime
    from django.conf import settings

    # Get parameters from POST request
    session_id = request.data.get('sessionId', '')
    event_id = request.data.get('eventId', '')
    persistent_id = request.data.get('persistentId', '')
    data = request.data.get('data', None)  # New field - can be null

    # Generate timestamp
    timestamp = datetime.now().isoformat()

    # Create analytics directory in media root or use a temp directory
    try:
        if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            analytics_dir = os.path.join(settings.MEDIA_ROOT, 'analytics')
        else:
            import tempfile
            analytics_dir = os.path.join(tempfile.gettempdir(), 'django_analytics')

        os.makedirs(analytics_dir, exist_ok=True)
        csv_file_path = os.path.join(analytics_dir, 'analytics.csv')

    except Exception as e:
        return Response({
            'error': 'Failed to create analytics directory',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    file_exists = os.path.isfile(csv_file_path)

    try:
        with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Timestamp', 'sessionId', 'eventId', 'persistentId', 'data']  # Added data field
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                'Timestamp': timestamp,
                'sessionId': session_id,
                'eventId': event_id,
                'persistentId': persistent_id,
                'data': data  # Added this field - will be empty string if None
            })

        return Response({
            'message': 'Analytics data logged successfully',
            'timestamp': timestamp
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': 'Failed to log analytics data',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)