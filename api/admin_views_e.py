"""
Admin Dashboard API Views - Phase E: Business Dashboard Analytics

Endpoints:
- GET /admin/business/overview/       - Main dashboard KPIs
- GET /admin/business/users/          - User growth and activity metrics
- GET /admin/business/content/        - Content catalog metrics
- GET /admin/business/engagement/     - Engagement/play metrics
- GET /admin/business/revenue/        - Revenue analytics
- GET /admin/business/geography/      - Geographic distribution
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Max, Min, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import (
    Player, Profile, Song, Artist, Label, Genre, Country,
    PlayerSongInstance, SongInstance, XsollaTransaction,
)
from .admin_utils import get_admin_user


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_overview(request):
    """
    GET /admin/business/overview/
    Returns flat shape matching AdminBusinessOverview.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    total_revenue = XsollaTransaction.objects.filter(
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    data = {
        'total_songs': Song.objects.count(),
        'active_songs': Song.objects.filter(status='active').count(),
        'total_artists': Artist.objects.count(),
        'total_players': Player.objects.count(),
        'total_transactions': XsollaTransaction.objects.filter(status='paid').count(),
        'total_revenue': str(total_revenue),
        'total_labels': Label.objects.count(),
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_users(request):
    """
    GET /admin/business/users/
    Returns flat shape matching AdminBusinessUsers.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    total_players = Player.objects.count()
    active_players = Player.objects.filter(status='active').count()
    frozen_players = Player.objects.filter(status='frozen').count()
    kicked_players = Player.objects.filter(status='kicked').count()

    # Players who have at least one paid transaction
    players_with_purchases = XsollaTransaction.objects.filter(
        status='paid'
    ).values('player').distinct().count()

    total_song_instances = PlayerSongInstance.objects.count()
    avg_songs_per_player = round(total_song_instances / total_players, 2) if total_players > 0 else 0

    data = {
        'total_players': total_players,
        'active_players': active_players,
        'frozen_players': frozen_players,
        'kicked_players': kicked_players,
        'players_with_purchases': players_with_purchases,
        'total_song_instances': total_song_instances,
        'avg_songs_per_player': avg_songs_per_player,
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_content(request):
    """
    GET /admin/business/content/
    Returns flat shape matching AdminBusinessContent.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    total_songs = Song.objects.count()
    active_songs = Song.objects.filter(status='active').count()
    inactive_songs = Song.objects.filter(status='inactive').count()
    total_artists = Artist.objects.count()

    # By platform: flat dict
    by_platform_qs = Song.objects.values('platform').annotate(count=Count('id'))
    by_platform = {item['platform'] or 'unknown': item['count'] for item in by_platform_qs}

    # By difficulty: flat dict
    by_difficulty_qs = Song.objects.values('difficulty').annotate(count=Count('id'))
    by_difficulty = {item['difficulty'] or 'unknown': item['count'] for item in by_difficulty_qs}

    # By country: array of {country, count}
    by_country_qs = Song.objects.values('country__name').annotate(
        count=Count('id')
    ).order_by('-count')
    by_country = [
        {'country': item['country__name'] or 'Unset', 'count': item['count']}
        for item in by_country_qs
    ]

    # Languages: array of {language, count}
    languages_qs = Song.objects.values('language').annotate(
        count=Count('id')
    ).order_by('-count')
    languages = [
        {'language': item['language'] or 'Unknown', 'count': item['count']}
        for item in languages_qs
    ]

    data = {
        'total_songs': total_songs,
        'active_songs': active_songs,
        'inactive_songs': inactive_songs,
        'total_artists': total_artists,
        'by_platform': by_platform,
        'by_difficulty': by_difficulty,
        'by_country': by_country,
        'languages': languages,
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_engagement(request):
    """
    GET /admin/business/engagement/
    Returns flat shape matching AdminBusinessEngagement.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    overall = PlayerSongInstance.objects.aggregate(
        total_plays=Sum('no_of_plays'),
        total_instances=Count('id'),
        avg_plays=Avg('no_of_plays'),
        avg_high_score=Avg('high_score'),
    )

    total_song_instances = overall['total_instances'] or 0
    total_plays = overall['total_plays'] or 0
    avg_plays_per_instance = round(overall['avg_plays'] or 0, 2)
    avg_high_score = round(overall['avg_high_score'] or 0, 1)

    # Top songs: {song_id, song_name, artist_name, total_plays, player_count}
    top_songs_qs = PlayerSongInstance.objects.values(
        'song__id', 'song__song_name', 'song__artist_name'
    ).annotate(
        total_plays=Sum('no_of_plays'),
        player_count=Count('player', distinct=True),
    ).order_by('-total_plays')[:15]

    top_songs = [
        {
            'song_id': item['song__id'],
            'song_name': item['song__song_name'],
            'artist_name': item['song__artist_name'],
            'total_plays': item['total_plays'] or 0,
            'player_count': item['player_count'] or 0,
        }
        for item in top_songs_qs
    ]

    # Top artists: {artist_name, total_plays, song_count}
    top_artists_qs = PlayerSongInstance.objects.values(
        'song__artist__name'
    ).annotate(
        total_plays=Sum('no_of_plays'),
        song_count=Count('song', distinct=True),
    ).order_by('-total_plays')[:10]

    top_artists = [
        {
            'artist_name': item['song__artist__name'] or 'Unknown',
            'total_plays': item['total_plays'] or 0,
            'song_count': item['song_count'] or 0,
        }
        for item in top_artists_qs
    ]

    data = {
        'total_song_instances': total_song_instances,
        'total_plays': total_plays,
        'avg_plays_per_instance': avg_plays_per_instance,
        'avg_high_score': avg_high_score,
        'top_songs': top_songs,
        'top_artists': top_artists,
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_revenue_analytics(request):
    """
    GET /admin/business/revenue/
    Returns flat shape matching AdminBusinessRevenue.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    overall = XsollaTransaction.objects.filter(status='paid').aggregate(
        total_revenue=Sum('amount'),
        total_transactions=Count('id'),
        total_discs=Sum('discs_granted'),
        total_gems=Sum('gems_granted'),
    )

    live_rev = XsollaTransaction.objects.filter(
        status='paid', is_sandbox=False
    ).aggregate(total=Sum('amount'))['total'] or 0

    sandbox_rev = XsollaTransaction.objects.filter(
        status='paid', is_sandbox=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Monthly breakdown: {month, count, total}
    monthly_qs = XsollaTransaction.objects.filter(
        status='paid'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        total=Sum('amount'),
    ).order_by('month')

    by_month = [
        {
            'month': item['month'].strftime('%Y-%m') if item['month'] else 'Unknown',
            'count': item['count'],
            'total': str(item['total'] or 0),
        }
        for item in monthly_qs
    ]

    data = {
        'total_transactions': overall['total_transactions'] or 0,
        'total_revenue': str(overall['total_revenue'] or 0),
        'live_revenue': str(live_rev),
        'sandbox_revenue': str(sandbox_rev),
        'total_discs_granted': overall['total_discs'] or 0,
        'total_gems_granted': overall['total_gems'] or 0,
        'by_month': by_month,
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def business_geography(request):
    """
    GET /admin/business/geography/
    Returns shape matching AdminBusinessGeography.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # songs_by_country: [{country, count}]
    songs_qs = Song.objects.values('country__name').annotate(
        count=Count('id')
    ).order_by('-count')
    songs_by_country = [
        {'country': item['country__name'] or 'Unset', 'count': item['count']}
        for item in songs_qs
    ]

    # players_by_country: [{country, count}]
    players_qs = Profile.objects.filter(
        country__isnull=False
    ).values('country__name').annotate(
        count=Count('id')
    ).order_by('-count')
    players_by_country = [
        {'country': item['country__name'], 'count': item['count']}
        for item in players_qs
    ]

    data = {
        'songs_by_country': songs_by_country,
        'players_by_country': players_by_country,
    }

    return Response(data)
