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

@api_view(['GET'])
def apiOverview(request):
    api_urls = {
        'List': '/song-list/',
        'Detail View': '/song-detail/<str:pk>/'
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
@permission_classes([permissions.IsAuthenticated])
def songList(request):
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
@permission_classes([permissions.IsAuthenticated])
def songDetail(request, pk):
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


@csrf_exempt
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


    refresh = RefreshToken.for_user(user)


    data = {}
    data['user'] = UserSerializer(user).data
    data['profile'] = ProfileSerializer(profile).data


    return Response({
        'message': 'User created successfully',
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,

    }, status=status.HTTP_201_CREATED)


@csrf_exempt
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

    profile = Profile.objects.get(user=user)
    refresh = RefreshToken.for_user(user)



    data = {}
    data['user'] = UserSerializer(user).data
    data['profile'] = ProfileSerializer(profile).data


    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,
    })


# Api to display artist detail 
# views.py
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def artist_detail(request, pk):
    print(f"Artist detail view called with ID: {pk}") 
    artist = get_object_or_404(Artist, pk=pk)
    serializer = ArtistSerializer(artist, context={'request': request})
    return Response(serializer.data)
