"""
Admin Dashboard API Views - Phase C: Content Enhancement (Songs/Artists CRUD)

Endpoints:
- GET    /admin/songs/                  - List songs with stats, search, filter
- POST   /admin/songs/create/           - Create a new song
- GET    /admin/songs/<pk>/             - Song detail with play stats
- PUT    /admin/songs/<pk>/update/      - Update a song
- DELETE /admin/songs/<pk>/delete/      - Delete a song (set inactive)
- GET    /admin/artists/                - List artists with stats, search, filter
- POST   /admin/artists/create/         - Create a new artist
- GET    /admin/artists/<pk>/           - Artist detail with songs and stats
- PUT    /admin/artists/<pk>/update/    - Update an artist
- DELETE /admin/artists/<pk>/delete/    - Delete an artist
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

from .models import Song, Artist, Label, Genre, Country, Tribe, PlayerSongInstance
from .admin_utils import get_admin_user, log_audit


# ============================================================
# SONG ENDPOINTS
# ============================================================

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def song_list(request):
    """
    GET /admin/songs/
    List all songs with play stats, search, and filters.

    Query params:
    - search: search by song_name or artist_name
    - status: filter by status (active/inactive)
    - label: filter by label name
    - country: filter by country name
    - genre: filter by genre name
    - sort: sort field (default: -id)
    - page, page_size: pagination
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    songs = Song.objects.select_related('artist', 'artist__label', 'genre', 'country', 'tribe').all()

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        songs = songs.filter(
            Q(song_name__icontains=search) |
            Q(artist_name__icontains=search) |
            Q(artist__name__icontains=search)
        )

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        songs = songs.filter(status=status_filter)

    label_filter = request.GET.get('label', '').strip()
    if label_filter:
        songs = songs.filter(artist__label__name__icontains=label_filter)

    country_filter = request.GET.get('country', '').strip()
    if country_filter:
        songs = songs.filter(country__name__icontains=country_filter)

    genre_filter = request.GET.get('genre', '').strip()
    if genre_filter:
        songs = songs.filter(genre__name__icontains=genre_filter)

    # Sorting
    sort = request.GET.get('sort', '-id').strip()
    allowed_sorts = ['id', '-id', 'song_name', '-song_name', 'date_added', '-date_added',
                     'artist_name', '-artist_name', 'difficulty', '-difficulty']
    if sort not in allowed_sorts:
        sort = '-id'
    songs = songs.order_by(sort)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = songs.count()
    start = (page - 1) * page_size
    end = start + page_size
    songs_page = songs[start:end]

    results = []
    for song in songs_page:
        # Play stats
        play_stats = PlayerSongInstance.objects.filter(song=song).aggregate(
            total_plays=Sum('no_of_plays'),
            unique_players=Count('player', distinct=True),
            avg_high_score=Avg('high_score'),
        )

        results.append({
            'id': song.id,
            'song_name': song.song_name,
            'artist_name': song.artist_name,
            'artist_id': song.artist_id,
            'label': song.artist.label.name if song.artist and song.artist.label else None,
            'genre': song.genre.name if song.genre else None,
            'country': song.country.name if song.country else None,
            'difficulty': song.difficulty,
            'status': song.status,
            'platform': song.platform,
            'promoted': song.promoted,
            'date_added': song.date_added.isoformat(),
            'go_live_date': song.go_live_date.isoformat() if song.go_live_date else None,
            'expiry_date': song.expiry_date.isoformat() if song.expiry_date else None,
            'language': song.language,
            'total_plays': play_stats['total_plays'] or 0,
            'unique_players': play_stats['unique_players'] or 0,
            'avg_high_score': round(play_stats['avg_high_score'] or 0, 1),
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def song_create(request):
    """
    POST /admin/songs/create/
    Create a new song.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager', 'content_editor'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data

    # Required fields
    song_name = data.get('song_name')
    artist_name = data.get('artist_name')
    if not song_name:
        return Response({'error': 'song_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Build song
    song = Song(
        song_name=song_name,
        artist_name=artist_name or '',
        difficulty=data.get('difficulty', 'medium'),
        status=data.get('status', 'active'),
        platform=data.get('platform', 'usiku'),
        promoted=data.get('promoted', False),
        language=data.get('language'),
        go_live_date=data.get('go_live_date'),
        expiry_date=data.get('expiry_date'),
    )

    # Optional FK lookups
    artist_id = data.get('artist_id')
    if artist_id:
        song.artist = Artist.objects.filter(id=artist_id).first()

    genre_id = data.get('genre_id')
    if genre_id:
        song.genre = Genre.objects.filter(id=genre_id).first()

    country_id = data.get('country_id')
    if country_id:
        song.country = Country.objects.filter(id=country_id).first()

    tribe_id = data.get('tribe_id')
    if tribe_id:
        song.tribe = Tribe.objects.filter(id=tribe_id).first()

    # URLs
    song.mp3_url = data.get('mp3_url')
    song.midi_url = data.get('midi_url')
    song.mp3_clip_url = data.get('mp3_clip_url')
    song.thumbnail_url = data.get('thumbnail_url')

    song.save()

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='song',
        entity_id=str(song.id),
        changes={'song_name': song.song_name, 'artist_name': song.artist_name},
        request=request,
    )

    return Response({
        'id': song.id,
        'song_name': song.song_name,
        'artist_name': song.artist_name,
        'status': song.status,
        'message': 'Song created successfully',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def song_detail(request, pk):
    """
    GET /admin/songs/<pk>/
    Song detail with full info and play statistics.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    song = get_object_or_404(
        Song.objects.select_related('artist', 'artist__label', 'genre', 'country', 'tribe'),
        pk=pk
    )

    # Play stats
    play_stats = PlayerSongInstance.objects.filter(song=song).aggregate(
        total_plays=Sum('no_of_plays'),
        unique_players=Count('player', distinct=True),
        avg_high_score=Avg('high_score'),
        favourited_count=Count('id', filter=Q(favourited=True)),
    )

    data = {
        'id': song.id,
        'song_name': song.song_name,
        'artist_name': song.artist_name,
        'artist': {
            'id': song.artist.id,
            'name': song.artist.name,
            'label': song.artist.label.name if song.artist.label else None,
        } if song.artist else None,
        'genre': {'id': song.genre.id, 'name': song.genre.name} if song.genre else None,
        'country': {'id': song.country.id, 'name': song.country.name} if song.country else None,
        'tribe': {'id': song.tribe.id, 'name': song.tribe.name} if song.tribe else None,
        'difficulty': song.difficulty,
        'status': song.status,
        'platform': song.platform,
        'promoted': song.promoted,
        'language': song.language,
        'date_added': song.date_added.isoformat(),
        'go_live_date': song.go_live_date.isoformat() if song.go_live_date else None,
        'expiry_date': song.expiry_date.isoformat() if song.expiry_date else None,
        'mp3_url': song.mp3_url,
        'midi_url': song.midi_url,
        'mp3_clip_url': song.mp3_clip_url,
        'thumbnail_url': song.thumbnail_url,
        'data': song.data,
        'stats': {
            'total_plays': play_stats['total_plays'] or 0,
            'unique_players': play_stats['unique_players'] or 0,
            'avg_high_score': round(play_stats['avg_high_score'] or 0, 1),
            'favourited_count': play_stats['favourited_count'] or 0,
        },
    }

    return Response(data)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.AllowAny])
def song_update(request, pk):
    """
    PUT/PATCH /admin/songs/<pk>/update/
    Update a song's fields.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager', 'content_editor'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    song = get_object_or_404(Song, pk=pk)
    data = request.data
    old_data = {'song_name': song.song_name, 'status': song.status}

    # Update simple fields
    simple_fields = ['song_name', 'artist_name', 'difficulty', 'status', 'platform',
                     'promoted', 'language', 'go_live_date', 'expiry_date',
                     'mp3_url', 'midi_url', 'mp3_clip_url', 'thumbnail_url']
    for field in simple_fields:
        if field in data:
            setattr(song, field, data[field])

    # FK updates
    if 'artist_id' in data:
        song.artist = Artist.objects.filter(id=data['artist_id']).first()
    if 'genre_id' in data:
        song.genre = Genre.objects.filter(id=data['genre_id']).first()
    if 'country_id' in data:
        song.country = Country.objects.filter(id=data['country_id']).first()
    if 'tribe_id' in data:
        song.tribe = Tribe.objects.filter(id=data['tribe_id']).first()

    song.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='song',
        entity_id=str(song.id),
        changes={'old': old_data, 'updated_fields': list(data.keys())},
        request=request,
    )

    return Response({
        'id': song.id,
        'song_name': song.song_name,
        'status': song.status,
        'message': 'Song updated successfully',
    })


@api_view(['DELETE'])
@permission_classes([permissions.AllowAny])
def song_delete(request, pk):
    """
    DELETE /admin/songs/<pk>/delete/
    Soft-delete a song by setting status to 'inactive'.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    song = get_object_or_404(Song, pk=pk)
    old_status = song.status
    song.status = 'inactive'
    song.save()

    log_audit(
        admin_email=admin.google_email,
        action='delete',
        entity_type='song',
        entity_id=str(song.id),
        changes={'song_name': song.song_name, 'old_status': old_status, 'new_status': 'inactive'},
        request=request,
    )

    return Response({'message': f'Song "{song.song_name}" set to inactive.', 'id': song.id})


# ============================================================
# ARTIST ENDPOINTS
# ============================================================

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def artist_list(request):
    """
    GET /admin/artists/
    List all artists with song counts, label, search and filters.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    artists = Artist.objects.select_related('label').annotate(
        song_count=Count('song'),
        total_plays=Sum('song__playersonginstance__no_of_plays'),
    )

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        artists = artists.filter(name__icontains=search)

    # Label filter
    label_filter = request.GET.get('label', '').strip()
    if label_filter:
        artists = artists.filter(label__name__icontains=label_filter)

    # Sorting
    sort = request.GET.get('sort', '-id').strip()
    allowed_sorts = ['id', '-id', 'name', '-name', 'song_count', '-song_count',
                     'total_plays', '-total_plays']
    if sort not in allowed_sorts:
        sort = '-id'
    artists = artists.order_by(sort)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = artists.count()
    start = (page - 1) * page_size
    end = start + page_size
    artists_page = artists[start:end]

    results = []
    for artist in artists_page:
        results.append({
            'id': artist.id,
            'name': artist.name,
            'label': artist.label.name if artist.label else None,
            'label_id': artist.label_id,
            'song_count': artist.song_count,
            'total_plays': artist.total_plays or 0,
            'bio': artist.bio,
            'revenue_earned': artist.revenue_earned,
            'current_balance': artist.current_balance,
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def artist_create(request):
    """
    POST /admin/artists/create/
    Create a new artist.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager', 'content_editor'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    name = data.get('name')
    if not name:
        return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

    artist = Artist(
        name=name,
        bio=data.get('bio', ''),
        spotify_link=data.get('spotify_link'),
        twitter_link=data.get('twitter_link'),
        youtube_link=data.get('youtube_link'),
        instagram_link=data.get('instagram_link'),
        website_link=data.get('website_link'),
    )

    label_id = data.get('label_id')
    if label_id:
        artist.label = Label.objects.filter(id=label_id).first()

    artist.save()

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='artist',
        entity_id=str(artist.id),
        changes={'name': artist.name, 'label': artist.label.name if artist.label else None},
        request=request,
    )

    return Response({
        'id': artist.id,
        'name': artist.name,
        'label': artist.label.name if artist.label else None,
        'message': 'Artist created successfully',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def artist_detail_admin(request, pk):
    """
    GET /admin/artists/<pk>/
    Artist detail with all songs and aggregated stats.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    artist = get_object_or_404(Artist.objects.select_related('label'), pk=pk)

    # Songs by this artist
    songs = Song.objects.filter(artist=artist).order_by('-date_added')
    songs_data = []
    for song in songs:
        play_stats = PlayerSongInstance.objects.filter(song=song).aggregate(
            total_plays=Sum('no_of_plays'),
            unique_players=Count('player', distinct=True),
        )
        songs_data.append({
            'id': song.id,
            'song_name': song.song_name,
            'difficulty': song.difficulty,
            'status': song.status,
            'date_added': song.date_added.isoformat(),
            'total_plays': play_stats['total_plays'] or 0,
            'unique_players': play_stats['unique_players'] or 0,
        })

    # Aggregate stats across all songs
    total_stats = PlayerSongInstance.objects.filter(song__artist=artist).aggregate(
        total_plays=Sum('no_of_plays'),
        unique_players=Count('player', distinct=True),
        avg_high_score=Avg('high_score'),
    )

    data = {
        'id': artist.id,
        'name': artist.name,
        'label': {'id': artist.label.id, 'name': artist.label.name} if artist.label else None,
        'bio': artist.bio,
        'spotify_link': artist.spotify_link,
        'twitter_link': artist.twitter_link,
        'youtube_link': artist.youtube_link,
        'instagram_link': artist.instagram_link,
        'website_link': artist.website_link,
        'revenue_earned': artist.revenue_earned,
        'current_balance': artist.current_balance,
        'data': artist.data,
        'stats': {
            'song_count': len(songs_data),
            'total_plays': total_stats['total_plays'] or 0,
            'unique_players': total_stats['unique_players'] or 0,
            'avg_high_score': round(total_stats['avg_high_score'] or 0, 1),
        },
        'songs': songs_data,
    }

    return Response(data)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.AllowAny])
def artist_update(request, pk):
    """
    PUT/PATCH /admin/artists/<pk>/update/
    Update an artist's fields.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager', 'content_editor'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    artist = get_object_or_404(Artist, pk=pk)
    data = request.data
    old_data = {'name': artist.name, 'label_id': artist.label_id}

    simple_fields = ['name', 'bio', 'spotify_link', 'twitter_link',
                     'youtube_link', 'instagram_link', 'website_link']
    for field in simple_fields:
        if field in data:
            setattr(artist, field, data[field])

    if 'label_id' in data:
        artist.label = Label.objects.filter(id=data['label_id']).first()

    artist.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='artist',
        entity_id=str(artist.id),
        changes={'old': old_data, 'updated_fields': list(data.keys())},
        request=request,
    )

    return Response({
        'id': artist.id,
        'name': artist.name,
        'label': artist.label.name if artist.label else None,
        'message': 'Artist updated successfully',
    })


@api_view(['DELETE'])
@permission_classes([permissions.AllowAny])
def artist_delete(request, pk):
    """
    DELETE /admin/artists/<pk>/delete/
    Delete an artist. Songs by this artist will have artist set to NULL.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    artist = get_object_or_404(Artist, pk=pk)
    artist_name = artist.name
    artist_id = artist.id

    # Count affected songs
    affected_songs = Song.objects.filter(artist=artist).count()

    artist.delete()

    log_audit(
        admin_email=admin.google_email,
        action='delete',
        entity_type='artist',
        entity_id=str(artist_id),
        changes={'name': artist_name, 'songs_orphaned': affected_songs},
        request=request,
    )

    return Response({
        'message': f'Artist "{artist_name}" deleted. {affected_songs} songs now unlinked.',
        'id': artist_id,
    })
