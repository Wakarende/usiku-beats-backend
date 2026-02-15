"""
Admin Dashboard API Views - Phase B: User Management

Endpoints:
- GET    /admin/users/              - List all players (with search, filter, pagination)
- GET    /admin/users/<pk>/         - Player detail (profile, play stats, transactions)
- POST   /admin/users/<pk>/freeze/  - Freeze a player account
- POST   /admin/users/<pk>/unfreeze/ - Unfreeze a player account
- POST   /admin/users/<pk>/kick/    - Kick a player (permanent removal)
- GET    /admin/users/export/       - Export user data as CSV
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
import csv
from django.http import HttpResponse

from .models import Player, Profile, PlayerSongInstance, XsollaTransaction, KickedPlayer
from .admin_utils import get_admin_user, log_audit


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def user_list(request):
    """
    GET /admin/users/
    List all players with optional search, filters, and pagination.

    Query params:
    - search: search by email or username
    - status: filter by player status (active, frozen, kicked)
    - sort: field to sort by (default: -id)
    - page: page number (default: 1)
    - page_size: items per page (default: 20)
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    players = Player.objects.select_related('profile', 'profile__user').all()

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        players = players.filter(
            Q(profile__user__email__icontains=search) |
            Q(profile__user__username__icontains=search) |
            Q(profile__user__first_name__icontains=search)
        )

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        players = players.filter(status=status_filter)

    # Sorting
    sort = request.GET.get('sort', '-id').strip()
    allowed_sorts = ['id', '-id', 'level', '-level', 'total_discs', '-total_discs',
                     'total_gems', '-total_gems', 'total_stars', '-total_stars']
    if sort not in allowed_sorts:
        sort = '-id'
    players = players.order_by(sort)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = players.count()
    start = (page - 1) * page_size
    end = start + page_size
    players_page = players[start:end]

    # Build response
    results = []
    for player in players_page:
        user = player.profile.user if player.profile else None
        song_count = PlayerSongInstance.objects.filter(player=player).count()
        total_plays = PlayerSongInstance.objects.filter(player=player).aggregate(
            total=Sum('no_of_plays'))['total'] or 0

        results.append({
            'id': player.id,
            'email': user.email if user else None,
            'username': user.username if user else None,
            'first_name': user.first_name if user else None,
            'date_joined': user.date_joined.isoformat() if user else None,
            'level': player.level,
            'total_discs': player.total_discs,
            'total_gems': player.total_gems,
            'total_stars': player.total_stars,
            'status': player.status,
            'songs_in_library': song_count,
            'total_plays': total_plays,
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def user_detail(request, pk):
    """
    GET /admin/users/<pk>/
    Detailed player profile including play stats and transaction history.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    player = get_object_or_404(
        Player.objects.select_related('profile', 'profile__user', 'profile__country'),
        pk=pk
    )

    user = player.profile.user if player.profile else None
    profile = player.profile

    # Song instances
    song_instances = PlayerSongInstance.objects.filter(player=player).select_related('song')
    songs_data = []
    for psi in song_instances:
        songs_data.append({
            'song_id': psi.song_id,
            'song_name': psi.song.song_name if psi.song else None,
            'artist_name': psi.song.artist_name if psi.song else None,
            'high_score': psi.high_score,
            'no_of_plays': psi.no_of_plays,
            'unlocked': psi.unlocked,
            'favourited': psi.favourited,
            'maximum_progress': psi.maximum_progress,
        })

    # Xsolla transactions
    transactions = XsollaTransaction.objects.filter(player=player).order_by('-created_at')[:20]
    transactions_data = []
    for tx in transactions:
        transactions_data.append({
            'id': tx.id,
            'order_id': tx.order_id,
            'status': tx.status,
            'amount': str(tx.amount),
            'currency': tx.currency,
            'discs_granted': tx.discs_granted,
            'gems_granted': tx.gems_granted,
            'is_sandbox': tx.is_sandbox,
            'created_at': tx.created_at.isoformat(),
        })

    # Kick history
    kicks = KickedPlayer.objects.filter(player=player).order_by('-kicked_at')
    kicks_data = []
    for k in kicks:
        kicks_data.append({
            'reason': k.reason,
            'kicked_by': k.kicked_by,
            'kicked_at': k.kicked_at.isoformat(),
        })

    data = {
        'id': player.id,
        'email': user.email if user else None,
        'username': user.username if user else None,
        'first_name': user.first_name if user else None,
        'date_joined': user.date_joined.isoformat() if user else None,
        'last_login': user.last_login.isoformat() if user and user.last_login else None,
        'level': player.level,
        'total_discs': player.total_discs,
        'total_gems': player.total_gems,
        'total_stars': player.total_stars,
        'calibration': player.calibration,
        'status': player.status,
        'profile': {
            'phone_number': profile.phone_number if profile else None,
            'google_id': profile.google_id if profile else None,
            'country': profile.country.name if profile and profile.country else None,
            'country_source': profile.country_source if profile else None,
            'ip_address': profile.recent_ip_address if profile else None,
        },
        'songs': songs_data,
        'transactions': transactions_data,
        'kick_history': kicks_data,
    }

    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_freeze(request, pk):
    """
    POST /admin/users/<pk>/freeze/
    Freeze a player account (prevents login/gameplay).
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can freeze users'}, status=status.HTTP_403_FORBIDDEN)

    player = get_object_or_404(Player, pk=pk)

    if player.status == 'frozen':
        return Response({'error': 'Player is already frozen'}, status=status.HTTP_400_BAD_REQUEST)

    if player.status == 'kicked':
        return Response({'error': 'Cannot freeze a kicked player'}, status=status.HTTP_400_BAD_REQUEST)

    old_status = player.status
    player.status = 'frozen'
    player.save()

    reason = request.data.get('reason', 'No reason provided')

    log_audit(
        admin_email=admin.google_email,
        action='freeze',
        entity_type='player',
        entity_id=str(player.id),
        changes={'old_status': old_status, 'new_status': 'frozen', 'reason': reason},
        request=request,
    )

    return Response({'message': f'Player {player.id} frozen.', 'status': 'frozen'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_unfreeze(request, pk):
    """
    POST /admin/users/<pk>/unfreeze/
    Unfreeze a previously frozen player account.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can unfreeze users'}, status=status.HTTP_403_FORBIDDEN)

    player = get_object_or_404(Player, pk=pk)

    if player.status != 'frozen':
        return Response({'error': 'Player is not frozen'}, status=status.HTTP_400_BAD_REQUEST)

    player.status = 'active'
    player.save()

    log_audit(
        admin_email=admin.google_email,
        action='unfreeze',
        entity_type='player',
        entity_id=str(player.id),
        changes={'old_status': 'frozen', 'new_status': 'active'},
        request=request,
    )

    return Response({'message': f'Player {player.id} unfrozen.', 'status': 'active'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_kick(request, pk):
    """
    POST /admin/users/<pk>/kick/
    Permanently kick a player from the platform.
    Body: { "reason": "..." }
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can kick users'}, status=status.HTTP_403_FORBIDDEN)

    player = get_object_or_404(Player, pk=pk)

    if player.status == 'kicked':
        return Response({'error': 'Player is already kicked'}, status=status.HTTP_400_BAD_REQUEST)

    reason = request.data.get('reason', '')
    if not reason:
        return Response({'error': 'A reason is required to kick a player'}, status=status.HTTP_400_BAD_REQUEST)

    old_status = player.status
    player.status = 'kicked'
    player.save()

    # Create kick record
    KickedPlayer.objects.create(
        player=player,
        reason=reason,
        kicked_by=admin.google_email,
    )

    log_audit(
        admin_email=admin.google_email,
        action='kick',
        entity_type='player',
        entity_id=str(player.id),
        changes={'old_status': old_status, 'new_status': 'kicked', 'reason': reason},
        request=request,
    )

    return Response({'message': f'Player {player.id} kicked.', 'status': 'kicked', 'reason': reason})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def user_export(request):
    """
    GET /admin/users/export/
    Export all player data as CSV download.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can export user data'}, status=status.HTTP_403_FORBIDDEN)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="usiku_beats_users_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Player ID', 'Email', 'Username', 'First Name', 'Date Joined',
        'Level', 'Total Discs', 'Total Gems', 'Total Stars', 'Status',
        'Songs in Library', 'Total Plays', 'Country', 'IP Address'
    ])

    players = Player.objects.select_related(
        'profile', 'profile__user', 'profile__country'
    ).all().order_by('id')

    for player in players:
        user = player.profile.user if player.profile else None
        profile = player.profile
        song_count = PlayerSongInstance.objects.filter(player=player).count()
        total_plays = PlayerSongInstance.objects.filter(player=player).aggregate(
            total=Sum('no_of_plays'))['total'] or 0

        writer.writerow([
            player.id,
            user.email if user else '',
            user.username if user else '',
            user.first_name if user else '',
            user.date_joined.isoformat() if user else '',
            player.level,
            player.total_discs,
            player.total_gems,
            player.total_stars,
            player.status,
            song_count,
            total_plays,
            profile.country.name if profile and profile.country else '',
            profile.recent_ip_address if profile else '',
        ])

    log_audit(
        admin_email=admin.google_email,
        action='export',
        entity_type='player',
        entity_id=None,
        changes={'format': 'csv', 'count': players.count()},
        request=request,
    )

    return response
