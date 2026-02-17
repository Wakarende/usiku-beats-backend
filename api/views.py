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
import requests as http_requests
from decimal import Decimal
from .utils import verify_xsolla_signature
from .constants import (
    XSOLLA_SKU_REWARDS,
    XSOLLA_PROJECT_ID,
    XSOLLA_MERCHANT_ID,
    XSOLLA_API_KEY,
)
import base64

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
    data['profile'] = ProfileSerializer(profile, context={'request': request}).data


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
    data['profile'] = ProfileSerializer(profile, context={'request': request}).data

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,
    })



@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_login(request):
    access_token = request.data.get('access_token')

    if not access_token:
        return Response({'error': 'access_token is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Verify the access token by fetching user info from Google
    try:
        google_response = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if google_response.status_code != 200:
            return Response({'error': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)

        google_data = google_response.json()
    except Exception:
        return Response({'error': 'Failed to verify Google token'}, status=status.HTTP_400_BAD_REQUEST)

    google_id = google_data.get('sub')
    email = google_data.get('email')
    name = google_data.get('name', '')

    if not google_id or not email:
        return Response({'error': 'Invalid token data'}, status=status.HTTP_400_BAD_REQUEST)

    ip_address = get_ip_address_from_request(request)

    # Check if a profile with this google_id already exists
    profile = Profile.objects.filter(google_id=google_id).first()

    if profile:
        # Existing Google user — log them in
        user = profile.user
    else:
        # Check if a user with this email already exists (email/password account)
        user = User.objects.filter(email=email).first()

        if user:
            # Link Google ID to existing account
            profile = Profile.objects.filter(user=user).first()
            if profile:
                profile.google_id = google_id
                profile.save()
            else:
                profile = Profile.objects.create(
                    user=user, google_id=google_id, recent_ip_address=ip_address
                )
                Player.objects.create(profile=profile)
        else:
            # Create a new user
            username = generate_unique_username(email)
            user = User.objects.create_user(
                username=username, email=email, password=None
            )
            user.first_name = name
            user.save()
            profile = Profile.objects.create(
                user=user, google_id=google_id, recent_ip_address=ip_address
            )
            Player.objects.create(profile=profile)

    refresh = RefreshToken.for_user(user)

    data = {}
    data['profile'] = ProfileSerializer(profile, context={'request': request}).data

    return Response({
        'message': 'Google login successful',
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'data': data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_player_data(request):
    from .serializers import PlayerSyncSerializer

    player = get_object_or_404(Player, profile=request.user.profile)
    serializer = PlayerSyncSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Update player fields if provided
    player_data = data.get('player', {})
    if 'level' in player_data:
        player.level = player_data['level']
    if 'total_discs' in player_data:
        player.total_discs = player_data['total_discs']
    if 'total_gems' in player_data:
        player.total_gems = player_data['total_gems']
    if 'total_stars' in player_data:
        player.total_stars = player_data['total_stars']
    player.save()

    # Upsert player song instances
    song_instances_data = data.get('player_song_instances', [])
    for instance_data in song_instances_data:
        song_id = instance_data.pop('song_id')
        song = Song.objects.filter(id=song_id).first()
        if not song:
            continue

        # Get or create the PlayerSongInstance
        psi, created = PlayerSongInstance.objects.get_or_create(
            player=player,
            song=song,
            defaults={
                'date_added': instance_data.get('date_added') or timezone.now(),
            }
        )

        # Update all provided fields
        if 'high_score' in instance_data:
            psi.high_score = instance_data['high_score']
        if 'no_of_plays' in instance_data:
            psi.no_of_plays = instance_data['no_of_plays']
        if 'favourited' in instance_data:
            psi.favourited = instance_data['favourited']
        if 'unlocked' in instance_data:
            psi.unlocked = instance_data['unlocked']
        if 'unlock_time' in instance_data:
            psi.unlock_time = instance_data['unlock_time']
        if 'unlock_start_time' in instance_data:
            psi.unlock_start_time = instance_data['unlock_start_time']
        if 'unlock_duration_sec' in instance_data:
            psi.unlock_duration_sec = instance_data['unlock_duration_sec']
        if 'unlock_completed_at' in instance_data:
            psi.unlock_completed_at = instance_data['unlock_completed_at']
        if 'maximum_progress' in instance_data:
            psi.maximum_progress = instance_data['maximum_progress']
        if 'paid_for_flag' in instance_data:
            psi.paid_for_flag = instance_data['paid_for_flag']
        if 'date_added' in instance_data and instance_data['date_added']:
            psi.date_added = instance_data['date_added']

        psi.save()

    # Return the full profile data (same as login response)
    profile = request.user.profile
    return Response({
        'profile': ProfileSerializer(profile, context={'request': request}).data
    }, status=status.HTTP_200_OK)
    

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_player_profile(request):
    """Read-only endpoint to fetch current player profile without pushing any data."""
    profile = request.user.profile
    return Response({
        'profile': ProfileSerializer(profile, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_player_songs(request):

    player = get_object_or_404(Player, profile=request.user.profile)
    instances = PlayerSongInstance.objects.filter(player=player)
    
    data = PlayerSongInstanceSerializer(instances, many=True, context={'request': request}).data
    return Response(data, status=status.HTTP_200_OK)


    
@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_player_song_instance(request, pk):
    player_song_instance = get_object_or_404(PlayerSongInstance, pk=pk)
    
    # Check if the user is authorized to update this instance
    if player_song_instance.player.profile.user != request.user:
        return Response({'error': 'You do not have permission to update this song instance.'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = PlayerSongInstanceSerializer(player_song_instance, data=request.data, partial=True, context={'request': request})
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
def library_songs(request):
    songs = Song.objects.filter(is_library=True, status='active').order_by('difficulty', 'song_name')
    serializer = SongSerializer(songs, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def xsolla_webhook(request):
    """
    Handle Xsolla payment webhooks.
    Supports: order_paid, order_canceled
    """
    # Verify signature first (before accessing request.data)
    is_valid, error_message = verify_xsolla_signature(request)
    if not is_valid:
        return Response({'error': error_message}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        data = request.data
        notification_type = data.get('notification_type')

        # Log all incoming webhooks for tracking
        WebhookLog.objects.create(
            source='xsolla',
            notification_type=notification_type,
            payload=data,
            ip_address=get_ip_address_from_request(request),
            headers=dict(request.headers),
        )

        # Handle order_paid
        if notification_type == 'order_paid':
            order = data.get('order', {})
            user_data = data.get('user', {})
            items = data.get('items', [])
            billing = data.get('billing', {})

            order_id = order.get('id')
            user_external_id = user_data.get('external_id')  # User's email

            # Check for duplicate (idempotency)
            existing_transaction = XsollaTransaction.objects.filter(order_id=order_id).first()
            if existing_transaction and existing_transaction.status == 'paid':
                return Response({'status': 'ok', 'message': 'Order already processed'})

            # Find the player by email
            user = User.objects.filter(email=user_external_id).first()
            if not user:
                return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

            profile = Profile.objects.filter(user=user).first()
            if not profile:
                return Response({'error': 'Profile not found'}, status=status.HTTP_400_BAD_REQUEST)

            player = Player.objects.filter(profile=profile).first()
            if not player:
                return Response({'error': 'Player not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate total rewards from all items
            total_discs = 0
            total_gems = 0

            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 1)
                rewards = XSOLLA_SKU_REWARDS.get(sku, {})
                total_discs += rewards.get('discs', 0) * quantity
                total_gems += rewards.get('gems', 0) * quantity

            # Grant the rewards
            player.total_discs += total_discs
            player.total_gems += total_gems
            player.save()
            player.refresh_from_db()

            # Record the transaction
            transaction = billing.get('transaction', {})
            XsollaTransaction.objects.create(
                order_id=order_id,
                invoice_id=order.get('invoice_id'),
                transaction_id=transaction.get('id'),
                player=player,
                user_external_id=user_external_id,
                status='paid',
                notification_type='order_paid',
                currency=order.get('currency', 'USD'),
                amount=Decimal(order.get('amount', '0')),
                discs_granted=total_discs,
                gems_granted=total_gems,
                webhook_payload=data,
                is_sandbox=(order.get('mode') == 'sandbox'),
            )

            return Response({
                'status': 'ok',
                'discs_granted': total_discs,
                'gems_granted': total_gems,
            })

        # # Handle order_canceled
        # elif notification_type == 'order_canceled':
        #     order = data.get('order', {})
        #     user_data = data.get('user', {})

        #     order_id = order.get('id')
        #     user_external_id = user_data.get('external_id')

        #     # Find the original paid transaction
        #     original_transaction = XsollaTransaction.objects.filter(
        #         order_id=order_id,
        #         status='paid'
        #     ).first()

        #     if not original_transaction:
        #         return Response({'status': 'ok', 'message': 'No paid transaction found to cancel'})

        #     # Check if already canceled
        #     if XsollaTransaction.objects.filter(order_id=order_id, status='canceled').exists():
        #         return Response({'status': 'ok', 'message': 'Order already canceled'})

        #     player = original_transaction.player
        #     if player:
        #         # Revoke the rewards (don't go negative)
        #         player.total_discs = max(0, player.total_discs - original_transaction.discs_granted)
        #         player.total_gems = max(0, player.total_gems - original_transaction.gems_granted)
        #         player.save()

        #     # Record the cancellation
        #     XsollaTransaction.objects.create(
        #         order_id=order_id,
        #         invoice_id=order.get('invoice_id'),
        #         transaction_id=original_transaction.transaction_id,
        #         player=player,
        #         user_external_id=user_external_id,
        #         status='canceled',
        #         notification_type='order_canceled',
        #         currency=order.get('currency', 'USD'),
        #         amount=Decimal(order.get('amount', '0')),
        #         discs_granted=-original_transaction.discs_granted,
        #         gems_granted=-original_transaction.gems_granted,
        #         webhook_payload=data,
        #         is_sandbox=(order.get('mode') == 'sandbox'),
        #     )

        #     return Response({
        #         'status': 'ok',
        #         'discs_revoked': original_transaction.discs_granted,
        #         'gems_revoked': original_transaction.gems_granted,
        #     })

        else:
            # Return success for unhandled notification types
            return Response({'status': 'ok', 'message': f'Notification type {notification_type} acknowledged'})

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_xsolla_payment_token(request):
    """
    Create a payment token for Xsolla checkout.
    Uses the authenticated user's email as external_id.
    """
    sku = request.data.get('sku')
    return_url = request.data.get('return_url', '')
    sandbox = request.data.get('sandbox', False)

    if not sku:
        return Response({'error': 'sku is required'}, status=status.HTTP_400_BAD_REQUEST)

    user_email = request.user.email
    user_ip = get_ip_address_from_request(request)

    # Create Basic auth header
    auth_string = f"{XSOLLA_MERCHANT_ID}:{XSOLLA_API_KEY}"
    auth_encoded = base64.b64encode(auth_string.encode()).decode()

    try:
        response = http_requests.post(
            f"https://store.xsolla.com/api/v3/project/{XSOLLA_PROJECT_ID}/admin/payment/token",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {auth_encoded}',
                'X-User-Ip': user_ip or '127.0.0.1'
            },
            json={
                'user': {
                    'id': {'value': user_email},
                    'email': {'value': user_email}
                },
                'purchase': {
                    'items': [{'sku': sku, 'quantity': 1}]
                },
                'sandbox': sandbox,
                'settings': {
                    'return_url': return_url
                }
            }
        )

        if not response.ok:
            return Response(
                {'error': 'Failed to create payment token', 'details': response.text},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = response.json()

        # Return token and payment URL
        payment_url = (
            f"https://sandbox-secure.xsolla.com/paystation4/?token={data['token']}"
            if sandbox
            else f"https://secure.xsolla.com/paystation4/?token={data['token']}"
        )

        return Response({
            'token': data['token'],
            'payment_url': payment_url
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)