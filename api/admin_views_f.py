"""
Admin Dashboard API Views - Phase F: Content Suggestions

Endpoints:
- GET    /admin/suggestions/                    - List content suggestions
- GET    /admin/suggestions/summary/            - Summary stats of suggestions
- POST   /admin/suggestions/<pk>/status/        - Update suggestion status (approve/reject)
- POST   /admin/suggestions/ingest/             - Ingest a suggestion (create song/artist from it)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from .models import ContentSuggestion, Song, Artist, Label, Genre, Country
from .admin_utils import get_admin_user, log_audit


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def suggestion_list(request):
    """
    GET /admin/suggestions/
    List content suggestions with optional filters.

    Query params:
    - status: filter by status (pending/approved/rejected)
    - type: filter by suggestion_type (song/artist/genre)
    - page, page_size: pagination
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    suggestions = ContentSuggestion.objects.all()

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        suggestions = suggestions.filter(status=status_filter)

    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        suggestions = suggestions.filter(suggestion_type=type_filter)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = suggestions.count()
    start = (page - 1) * page_size
    end = start + page_size
    suggestions_page = suggestions[start:end]

    results = []
    for s in suggestions_page:
        results.append({
            'id': s.id,
            'suggestion_type': s.suggestion_type,
            'title': s.title,
            'detail': s.detail,
            'status': s.status,
            'reviewed_by': s.reviewed_by,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat(),
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def suggestion_summary(request):
    """
    GET /admin/suggestions/summary/
    Summary stats: counts by status and type.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    by_status = ContentSuggestion.objects.values('status').annotate(count=Count('id'))
    by_type = ContentSuggestion.objects.values('suggestion_type').annotate(count=Count('id'))

    data = {
        'total': ContentSuggestion.objects.count(),
        'by_status': {item['status']: item['count'] for item in by_status},
        'by_type': {item['suggestion_type']: item['count'] for item in by_type},
    }

    return Response(data)


@api_view(['POST'])
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

    new_status = request.data.get('status')
    if new_status not in ('approved', 'rejected'):
        return Response({'error': 'status must be "approved" or "rejected"'},
                        status=status.HTTP_400_BAD_REQUEST)

    old_status = suggestion.status
    suggestion.status = new_status
    suggestion.reviewed_by = admin.google_email
    suggestion.save()

    log_audit(
        admin_email=admin.google_email,
        action='update_status',
        entity_type='content_suggestion',
        entity_id=str(suggestion.id),
        changes={'old_status': old_status, 'new_status': new_status},
        request=request,
    )

    return Response({
        'id': suggestion.id,
        'title': suggestion.title,
        'status': suggestion.status,
        'message': f'Suggestion {new_status}.',
    })


@api_view(['POST'])
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
    detail = suggestion.detail or {}

    created_entity = None

    if suggestion.suggestion_type == 'song':
        song = Song(
            song_name=overrides.get('song_name', detail.get('song_name', suggestion.title)),
            artist_name=overrides.get('artist_name', detail.get('artist_name', '')),
            difficulty=overrides.get('difficulty', detail.get('difficulty', 'medium')),
            status='active',
            platform='usiku',
            language=overrides.get('language', detail.get('language')),
        )

        # Link artist if provided
        artist_id = overrides.get('artist_id', detail.get('artist_id'))
        if artist_id:
            song.artist = Artist.objects.filter(id=artist_id).first()

        # Link genre if provided
        genre_id = overrides.get('genre_id', detail.get('genre_id'))
        if genre_id:
            song.genre = Genre.objects.filter(id=genre_id).first()

        # Link country if provided
        country_id = overrides.get('country_id', detail.get('country_id'))
        if country_id:
            song.country = Country.objects.filter(id=country_id).first()

        song.save()
        created_entity = {'type': 'song', 'id': song.id, 'name': song.song_name}

    elif suggestion.suggestion_type == 'artist':
        artist = Artist(
            name=overrides.get('name', detail.get('name', suggestion.title)),
            bio=overrides.get('bio', detail.get('bio', '')),
        )

        label_id = overrides.get('label_id', detail.get('label_id'))
        if label_id:
            artist.label = Label.objects.filter(id=label_id).first()

        artist.save()
        created_entity = {'type': 'artist', 'id': artist.id, 'name': artist.name}

    elif suggestion.suggestion_type == 'genre':
        genre_name = overrides.get('name', detail.get('name', suggestion.title))
        genre, created = Genre.objects.get_or_create(name=genre_name)
        created_entity = {'type': 'genre', 'id': genre.id, 'name': genre.name, 'was_new': created}

    else:
        return Response({'error': f'Unknown suggestion type: {suggestion.suggestion_type}'},
                        status=status.HTTP_400_BAD_REQUEST)

    log_audit(
        admin_email=admin.google_email,
        action='ingest',
        entity_type='content_suggestion',
        entity_id=str(suggestion.id),
        changes={'suggestion_title': suggestion.title, 'created': created_entity},
        request=request,
    )

    return Response({
        'message': f'Suggestion ingested successfully.',
        'suggestion_id': suggestion.id,
        'created': created_entity,
    }, status=status.HTTP_201_CREATED)
