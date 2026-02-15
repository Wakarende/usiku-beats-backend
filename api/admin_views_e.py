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
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Max, Min, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from .models import (
    Player, Profile, Song, Artist, Label, Genre, Country,
    PlayerSongInstance, SongInstance, XsollaTransaction,
)
from .admin_utils import get_admin_user


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_overview(request):
    """
    GET /admin/business/overview/
    Main dashboard KPIs: total users, songs, artists, revenue, etc.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Core counts
    total_players = Player.objects.count()
    active_players = Player.objects.filter(status='active').count()
    total_songs = Song.objects.count()
    active_songs = Song.objects.filter(status='active').count()
    total_artists = Artist.objects.count()

    # Play stats
    total_plays = PlayerSongInstance.objects.aggregate(
        total=Sum('no_of_plays'))['total'] or 0

    # Revenue
    total_revenue = XsollaTransaction.objects.filter(
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Label distribution
    label_dist = Artist.objects.values('label__name').annotate(
        count=Count('id')
    ).order_by('-count')

    data = {
        'players': {
            'total': total_players,
            'active': active_players,
        },
        'content': {
            'total_songs': total_songs,
            'active_songs': active_songs,
            'total_artists': total_artists,
        },
        'engagement': {
            'total_plays': total_plays,
        },
        'revenue': {
            'total': str(total_revenue),
        },
        'labels': [
            {'name': item['label__name'] or 'Unassigned', 'count': item['count']}
            for item in label_dist
        ],
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_users(request):
    """
    GET /admin/business/users/
    User growth and activity metrics.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Status breakdown
    status_breakdown = Player.objects.values('status').annotate(
        count=Count('id')
    )

    # Level distribution
    level_dist = Player.objects.values('level').annotate(
        count=Count('id')
    ).order_by('level')

    # Average stats
    avg_stats = Player.objects.aggregate(
        avg_level=Avg('level'),
        avg_discs=Avg('total_discs'),
        avg_gems=Avg('total_gems'),
        avg_stars=Avg('total_stars'),
        max_level=Max('level'),
    )

    # Top players by level
    top_players = Player.objects.select_related(
        'profile__user'
    ).order_by('-level', '-total_stars')[:10]
    top_data = []
    for p in top_players:
        user = p.profile.user if p.profile else None
        top_data.append({
            'id': p.id,
            'email': user.email if user else None,
            'level': p.level,
            'total_stars': p.total_stars,
            'total_discs': p.total_discs,
            'total_gems': p.total_gems,
        })

    data = {
        'total_players': Player.objects.count(),
        'status_breakdown': {
            item['status']: item['count'] for item in status_breakdown
        },
        'level_distribution': [
            {'level': item['level'], 'count': item['count']}
            for item in level_dist
        ],
        'averages': {
            'avg_level': round(avg_stats['avg_level'] or 0, 1),
            'avg_discs': round(avg_stats['avg_discs'] or 0, 1),
            'avg_gems': round(avg_stats['avg_gems'] or 0, 1),
            'avg_stars': round(avg_stats['avg_stars'] or 0, 1),
            'max_level': avg_stats['max_level'] or 0,
        },
        'top_players': top_data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_content(request):
    """
    GET /admin/business/content/
    Content catalog metrics: songs by status, genre, country, label.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Songs by status
    by_status = Song.objects.values('status').annotate(count=Count('id'))

    # Songs by difficulty
    by_difficulty = Song.objects.values('difficulty').annotate(count=Count('id'))

    # Songs by genre
    by_genre = Song.objects.values('genre__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Songs by country
    by_country = Song.objects.values('country__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Songs by label
    by_label = Song.objects.values('artist__label__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Songs by platform
    by_platform = Song.objects.values('platform').annotate(count=Count('id'))

    # Artists by label
    artists_by_label = Artist.objects.values('label__name').annotate(
        count=Count('id')
    ).order_by('-count')

    data = {
        'songs': {
            'total': Song.objects.count(),
            'by_status': {item['status']: item['count'] for item in by_status},
            'by_difficulty': {item['difficulty']: item['count'] for item in by_difficulty},
            'by_genre': [
                {'name': item['genre__name'] or 'Unset', 'count': item['count']}
                for item in by_genre
            ],
            'by_country': [
                {'name': item['country__name'] or 'Unset', 'count': item['count']}
                for item in by_country
            ],
            'by_label': [
                {'name': item['artist__label__name'] or 'Unlinked', 'count': item['count']}
                for item in by_label
            ],
            'by_platform': {item['platform']: item['count'] for item in by_platform},
        },
        'artists': {
            'total': Artist.objects.count(),
            'by_label': [
                {'name': item['label__name'] or 'Unassigned', 'count': item['count']}
                for item in artists_by_label
            ],
        },
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_engagement(request):
    """
    GET /admin/business/engagement/
    Engagement and play metrics.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Overall play stats
    overall = PlayerSongInstance.objects.aggregate(
        total_plays=Sum('no_of_plays'),
        total_instances=Count('id'),
        avg_plays_per_song=Avg('no_of_plays'),
        avg_high_score=Avg('high_score'),
        total_favourited=Count('id', filter=Q(favourited=True)),
        total_unlocked=Count('id', filter=Q(unlocked=True)),
    )

    # Top songs by plays
    top_songs = PlayerSongInstance.objects.values(
        'song__id', 'song__song_name', 'song__artist_name'
    ).annotate(
        total_plays=Sum('no_of_plays'),
        unique_players=Count('player', distinct=True),
        avg_score=Avg('high_score'),
    ).order_by('-total_plays')[:15]

    top_songs_data = []
    for item in top_songs:
        top_songs_data.append({
            'song_id': item['song__id'],
            'song_name': item['song__song_name'],
            'artist_name': item['song__artist_name'],
            'total_plays': item['total_plays'] or 0,
            'unique_players': item['unique_players'] or 0,
            'avg_score': round(item['avg_score'] or 0, 1),
        })

    # Top artists by plays
    top_artists = PlayerSongInstance.objects.values(
        'song__artist__id', 'song__artist__name'
    ).annotate(
        total_plays=Sum('no_of_plays'),
        unique_players=Count('player', distinct=True),
    ).order_by('-total_plays')[:10]

    top_artists_data = []
    for item in top_artists:
        top_artists_data.append({
            'artist_id': item['song__artist__id'],
            'artist_name': item['song__artist__name'],
            'total_plays': item['total_plays'] or 0,
            'unique_players': item['unique_players'] or 0,
        })

    data = {
        'overview': {
            'total_plays': overall['total_plays'] or 0,
            'total_song_instances': overall['total_instances'] or 0,
            'avg_plays_per_song': round(overall['avg_plays_per_song'] or 0, 1),
            'avg_high_score': round(overall['avg_high_score'] or 0, 1),
            'total_favourited': overall['total_favourited'] or 0,
            'total_unlocked': overall['total_unlocked'] or 0,
        },
        'top_songs': top_songs_data,
        'top_artists': top_artists_data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_revenue_analytics(request):
    """
    GET /admin/business/revenue/
    Revenue analytics: totals, by period, sandbox vs live.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Overall
    overall = XsollaTransaction.objects.filter(status='paid').aggregate(
        total_revenue=Sum('amount'),
        total_transactions=Count('id'),
        total_discs=Sum('discs_granted'),
        total_gems=Sum('gems_granted'),
    )

    # Sandbox vs live
    sandbox_stats = XsollaTransaction.objects.filter(
        status='paid', is_sandbox=True
    ).aggregate(
        count=Count('id'),
        total=Sum('amount'),
    )

    live_stats = XsollaTransaction.objects.filter(
        status='paid', is_sandbox=False
    ).aggregate(
        count=Count('id'),
        total=Sum('amount'),
    )

    # Monthly breakdown
    monthly = XsollaTransaction.objects.filter(
        status='paid'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        total=Sum('amount'),
    ).order_by('month')

    monthly_data = []
    for item in monthly:
        monthly_data.append({
            'month': item['month'].isoformat() if item['month'] else None,
            'transactions': item['count'],
            'revenue': str(item['total'] or 0),
        })

    data = {
        'overall': {
            'total_revenue': str(overall['total_revenue'] or 0),
            'total_transactions': overall['total_transactions'] or 0,
            'total_discs_granted': overall['total_discs'] or 0,
            'total_gems_granted': overall['total_gems'] or 0,
        },
        'sandbox': {
            'transactions': sandbox_stats['count'] or 0,
            'revenue': str(sandbox_stats['total'] or 0),
        },
        'live': {
            'transactions': live_stats['count'] or 0,
            'revenue': str(live_stats['total'] or 0),
        },
        'monthly': monthly_data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def business_geography(request):
    """
    GET /admin/business/geography/
    Geographic distribution of content and users.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Songs by country
    songs_by_country = Song.objects.values(
        'country__name', 'country__code'
    ).annotate(
        song_count=Count('id'),
        total_plays=Sum('playersonginstance__no_of_plays'),
    ).order_by('-song_count')

    songs_geo = []
    for item in songs_by_country:
        songs_geo.append({
            'country': item['country__name'] or 'Unset',
            'code': item['country__code'] or '',
            'song_count': item['song_count'],
            'total_plays': item['total_plays'] or 0,
        })

    # Users by country (from profile.country)
    users_by_country = Profile.objects.filter(
        country__isnull=False
    ).values(
        'country__name', 'country__code'
    ).annotate(
        user_count=Count('id'),
    ).order_by('-user_count')

    users_geo = []
    for item in users_by_country:
        users_geo.append({
            'country': item['country__name'],
            'code': item['country__code'] or '',
            'user_count': item['user_count'],
        })

    # Countries in system
    countries = Country.objects.annotate(
        song_count=Count('song'),
        tribe_count=Count('tribe'),
    ).order_by('name')
    countries_data = []
    for c in countries:
        countries_data.append({
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'song_count': c.song_count,
            'tribe_count': c.tribe_count,
        })

    data = {
        'songs_by_country': songs_geo,
        'users_by_country': users_geo,
        'countries': countries_data,
    }

    return Response(data)
