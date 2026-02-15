"""
Admin Dashboard API Views - Phase F: Content Suggestions

Endpoints:
- GET    /admin/suggestions/                    - List content suggestions
- GET    /admin/suggestions/summary/            - Summary stats of suggestions
- POST   /admin/suggestions/<pk>/status/        - Update suggestion status (approve/reject)
- POST   /admin/suggestions/ingest/             - Ingest a suggestion (create song/artist from it)
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone

from .models import ContentSuggestion, Song, Artist, Label, Genre, Country
from .admin_utils import get_admin_user, log_audit


def _map_status(db_status):
    """Map DB status values to frontend expected values."""
    mapping = {
        'new': 'pending',
        'approved': 'approved',
        'dismissed': 'rejected',
    }
    return mapping.get(db_status, db_status)


def _reverse_map_status(frontend_status):
    """Map frontend status values back to DB values."""
    mapping = {
        'pending': 'new',
        'approved': 'approved',
        'rejected': 'dismissed',
    }
    return mapping.get(frontend_status, frontend_status)


def _serialize_suggestion(s):
    """Serialize a ContentSuggestion to match AdminSuggestion frontend type."""
    detail = {
        'artist_name': s.artist_name,
        'genre': s.genre,
        'peak_position': s.peak_position,
        'current_popularity': s.current_popularity,
        'weeks_trending': s.weeks_trending,
        'external_id': s.external_id,
    }
    if s.chart_regions:
        detail['chart_regions'] = s.chart_regions
    if s.data:
        detail['extra'] = s.data

    return {
        'id': s.id,
        'suggestion_type': s.external_source or 'unknown',
        'title': s.song_title,
        'detail': detail,
        'status': _map_status(s.status),
        'reviewed_by': s.acted_by.google_email if s.acted_by else None,
        'created_at': s.first_seen.isoformat() if s.first_seen else None,
        'updated_at': s.acted_at.isoformat() if s.acted_at else (s.first_seen.isoformat() if s.first_seen else None),
    }


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def suggestion_list(request):
    """
    GET /admin/suggestions/
    List content suggestions with optional filters.

    Query params:
    - status: filter by status (pending/approved/rejected) — mapped to DB values
    - type: filter by external_source
    - page, page_size: pagination
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    suggestions = ContentSuggestion.objects.select_related('acted_by').all()

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        db_status = _reverse_map_status(status_filter)
        suggestions = suggestions.filter(status=db_status)

    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        suggestions = suggestions.filter(external_source=type_filter)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = suggestions.count()
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    suggestions_page = suggestions[start_idx:end_idx]

    results = [_serialize_suggestion(s) for s in suggestions_page]

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def suggestion_summary(request):
    """
    GET /admin/suggestions/summary/
    Summary stats: counts by status and type.
    Maps DB statuses to frontend statuses.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    by_status_raw = ContentSuggestion.objects.values('status').annotate(count=Count('id'))
    by_type_raw = ContentSuggestion.objects.values('external_source').annotate(count=Count('id'))

    # Map DB status to frontend status
    by_status = {}
    for item in by_status_raw:
        frontend_status = _map_status(item['status'])
        by_status[frontend_status] = by_status.get(frontend_status, 0) + item['count']

    by_type = {item['external_source']: item['count'] for item in by_type_raw}

    data = {
        'total': ContentSuggestion.objects.count(),
        'by_status': by_status,
        'by_type': by_type,
    }

    return Response(data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def suggestion_update_status(request, pk):
    """
    POST /admin/suggestions/<pk>/status/
    Approve or reject a content suggestion.
    Body: { "status": "approved" | "rejected" }
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    suggestion = get_object_or_404(ContentSuggestion, pk=pk)

    new_status_frontend = request.data.get('status')
    if new_status_frontend not in ('approved', 'rejected'):
        return Response({'error': 'status must be "approved" or "rejected"'},
                        status=status.HTTP_400_BAD_REQUEST)

    new_status_db = _reverse_map_status(new_status_frontend)
    old_status = suggestion.status
    suggestion.status = new_status_db
    suggestion.acted_by = admin
    suggestion.acted_at = timezone.now()

    if new_status_frontend == 'rejected':
        suggestion.dismissed_reason = request.data.get('reason', '')

    suggestion.save()

    log_audit(
        admin_email=admin.google_email,
        action='update_status',
        entity_type='content_suggestion',
        entity_id=str(suggestion.id),
        changes={'old_status': _map_status(old_status), 'new_status': new_status_frontend},
        request=request,
    )

    return Response({
        'id': suggestion.id,
        'title': suggestion.song_title,
        'status': _map_status(suggestion.status),
        'message': f'Suggestion {new_status_frontend}.',
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def suggestion_ingest(request):
    """
    POST /admin/suggestions/ingest/
    Ingest a content suggestion — create the actual song/artist from it.
    Body: { "suggestion_id": <int>, "overrides": { ... optional field overrides } }
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    suggestion_id = request.data.get('suggestion_id')
    if not suggestion_id:
        return Response({'error': 'suggestion_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    suggestion = get_object_or_404(ContentSuggestion, pk=suggestion_id)

    if suggestion.status != 'approved':
        return Response({'error': 'Only approved suggestions can be ingested'},
                        status=status.HTTP_400_BAD_REQUEST)

    overrides = request.data.get('overrides', {})

    # Create a song from the suggestion
    song = Song(
        song_name=overrides.get('song_name', suggestion.song_title),
        artist_name=overrides.get('artist_name', suggestion.artist_name),
        difficulty=overrides.get('difficulty', 'medium'),
        status='active',
        platform='usiku',
        language=overrides.get('language'),
    )

    # Link artist if provided
    artist_id = overrides.get('artist_id')
    if artist_id:
        song.artist = Artist.objects.filter(id=artist_id).first()

    # Link genre if provided
    genre_name = overrides.get('genre', suggestion.genre)
    if genre_name:
        genre_obj = Genre.objects.filter(name__iexact=genre_name).first()
        if genre_obj:
            song.genre = genre_obj

    song.save()

    # Link the suggestion to the created song
    suggestion.linked_song = song
    suggestion.acted_by = admin
    suggestion.acted_at = timezone.now()
    suggestion.save()

    created_entity = {'type': 'song', 'id': song.id, 'name': song.song_name}

    log_audit(
        admin_email=admin.google_email,
        action='ingest',
        entity_type='content_suggestion',
        entity_id=str(suggestion.id),
        changes={'suggestion_title': suggestion.song_title, 'created': created_entity},
        request=request,
    )

    return Response({
        'message': 'Suggestion ingested successfully.',
        'suggestion_id': suggestion.id,
        'created': created_entity,
    }, status=status.HTTP_201_CREATED)
