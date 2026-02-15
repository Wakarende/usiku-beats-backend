"""
Admin Dashboard API Views - Phase D: Revenue Dashboard

Endpoints:
- GET    /admin/revenue/payees/                - List all payees (artists with revenue data)
- GET    /admin/revenue/payees/<pk>/           - Payee detail with payment history
- GET    /admin/revenue/payments/              - List all payment statuses
- POST   /admin/revenue/payments/create/       - Create a new payment record
- PUT    /admin/revenue/payments/<pk>/update/  - Update payment status
- GET    /admin/revenue/export/                - Export revenue data as CSV
- GET    /admin/revenue/summary/               - Revenue summary/overview
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
import csv
from django.http import HttpResponse

from .models import Artist, Payout, PaymentStatus, XsollaTransaction
from .admin_utils import get_admin_user, log_audit


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def revenue_payee_list(request):
    """
    GET /admin/revenue/payees/
    List artists as payees with their revenue and balance info.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    artists = Artist.objects.select_related('label').annotate(
        song_count=Count('song'),
        payout_count=Count('payout'),
    ).order_by('-revenue_earned')

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        artists = artists.filter(name__icontains=search)

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
            'song_count': artist.song_count,
            'revenue_earned': artist.revenue_earned or 0,
            'current_balance': artist.current_balance or 0,
            'payout_count': artist.payout_count,
            'preferred_payout_method': artist.preferred_payout_method,
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def revenue_payee_detail(request, pk):
    """
    GET /admin/revenue/payees/<pk>/
    Payee detail with full payout history and payment statuses.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    artist = get_object_or_404(Artist.objects.select_related('label'), pk=pk)

    # Payout history
    payouts = Payout.objects.filter(artist=artist).order_by('-date')
    payouts_data = []
    for p in payouts:
        payouts_data.append({
            'id': p.id,
            'date': p.date.isoformat(),
            'method': p.method,
            'receipt_url': p.receipt_url,
        })

    # Payment statuses
    payment_statuses = PaymentStatus.objects.filter(artist=artist).order_by('-created_at')
    payments_data = []
    for ps in payment_statuses:
        payments_data.append({
            'id': ps.id,
            'period_start': ps.period_start.isoformat(),
            'period_end': ps.period_end.isoformat(),
            'amount': str(ps.amount),
            'currency': ps.currency,
            'status': ps.status,
            'initiated_by': ps.initiated_by,
            'notes': ps.notes,
            'created_at': ps.created_at.isoformat(),
        })

    data = {
        'id': artist.id,
        'name': artist.name,
        'label': artist.label.name if artist.label else None,
        'revenue_earned': artist.revenue_earned or 0,
        'current_balance': artist.current_balance or 0,
        'preferred_payout_method': artist.preferred_payout_method,
        'mpesa_number': artist.mpesa_number,
        'payouts': payouts_data,
        'payment_statuses': payments_data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def payment_status_list(request):
    """
    GET /admin/revenue/payments/
    List all payment status records with optional filters.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    payments = PaymentStatus.objects.select_related('artist').all()

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        payments = payments.filter(status=status_filter)

    artist_id = request.GET.get('artist_id', '').strip()
    if artist_id:
        payments = payments.filter(artist_id=artist_id)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    total = payments.count()
    start = (page - 1) * page_size
    end = start + page_size
    payments_page = payments[start:end]

    results = []
    for ps in payments_page:
        results.append({
            'id': ps.id,
            'artist_id': ps.artist_id,
            'artist_name': ps.artist.name if ps.artist else None,
            'period_start': ps.period_start.isoformat(),
            'period_end': ps.period_end.isoformat(),
            'amount': str(ps.amount),
            'currency': ps.currency,
            'status': ps.status,
            'initiated_by': ps.initiated_by,
            'notes': ps.notes,
            'created_at': ps.created_at.isoformat(),
        })

    return Response({
        'results': results,
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def payment_status_create(request):
    """
    POST /admin/revenue/payments/create/
    Create a new payment status record.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can create payments'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    artist_id = data.get('artist_id')
    if not artist_id:
        return Response({'error': 'artist_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    artist = Artist.objects.filter(id=artist_id).first()
    if not artist:
        return Response({'error': 'Artist not found'}, status=status.HTTP_404_NOT_FOUND)

    required = ['period_start', 'period_end', 'amount']
    for field in required:
        if not data.get(field):
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)

    payment = PaymentStatus.objects.create(
        artist=artist,
        period_start=data['period_start'],
        period_end=data['period_end'],
        amount=data['amount'],
        currency=data.get('currency', 'USD'),
        status=data.get('status', 'pending'),
        initiated_by=admin.google_email,
        notes=data.get('notes', ''),
    )

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='payment_status',
        entity_id=str(payment.id),
        changes={'artist': artist.name, 'amount': str(payment.amount), 'status': payment.status},
        request=request,
    )

    return Response({
        'id': payment.id,
        'artist_name': artist.name,
        'amount': str(payment.amount),
        'status': payment.status,
        'message': 'Payment record created.',
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.AllowAny])
def payment_status_update(request, pk):
    """
    PUT/PATCH /admin/revenue/payments/<pk>/update/
    Update a payment status record (mainly status transitions).
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can update payments'}, status=status.HTTP_403_FORBIDDEN)

    payment = get_object_or_404(PaymentStatus, pk=pk)
    data = request.data
    old_status = payment.status

    if 'status' in data:
        payment.status = data['status']
    if 'notes' in data:
        payment.notes = data['notes']
    if 'amount' in data:
        payment.amount = data['amount']

    payment.save()

    log_audit(
        admin_email=admin.google_email,
        action='update',
        entity_type='payment_status',
        entity_id=str(payment.id),
        changes={'old_status': old_status, 'new_status': payment.status},
        request=request,
    )

    return Response({
        'id': payment.id,
        'status': payment.status,
        'message': 'Payment record updated.',
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def revenue_export(request):
    """
    GET /admin/revenue/export/
    Export revenue/transaction data as CSV.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role != 'super_user':
        return Response({'error': 'Only super_user can export revenue data'}, status=status.HTTP_403_FORBIDDEN)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="usiku_beats_revenue_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Order ID', 'Player Email', 'Status',
        'Amount', 'Currency', 'Discs Granted', 'Gems Granted',
        'Is Sandbox', 'Created At'
    ])

    transactions = XsollaTransaction.objects.all().order_by('-created_at')
    for tx in transactions:
        writer.writerow([
            tx.id,
            tx.order_id,
            tx.user_external_id,
            tx.status,
            str(tx.amount),
            tx.currency,
            tx.discs_granted,
            tx.gems_granted,
            tx.is_sandbox,
            tx.created_at.isoformat(),
        ])

    log_audit(
        admin_email=admin.google_email,
        action='export',
        entity_type='revenue',
        entity_id=None,
        changes={'format': 'csv', 'count': transactions.count()},
        request=request,
    )

    return response


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def revenue_summary(request):
    """
    GET /admin/revenue/summary/
    Revenue summary/overview with aggregated metrics.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Transaction stats
    tx_stats = XsollaTransaction.objects.filter(status='paid').aggregate(
        total_revenue=Sum('amount'),
        total_transactions=Count('id'),
        total_discs_granted=Sum('discs_granted'),
        total_gems_granted=Sum('gems_granted'),
    )

    # Payment status breakdown
    payment_stats = PaymentStatus.objects.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('amount'),
    )
    payment_breakdown = {}
    for ps in payment_stats:
        payment_breakdown[ps['status']] = {
            'count': ps['count'],
            'total_amount': str(ps['total_amount'] or 0),
        }

    # Artists with balance
    artists_with_balance = Artist.objects.filter(
        current_balance__gt=0
    ).count()

    total_outstanding = Artist.objects.filter(
        current_balance__gt=0
    ).aggregate(total=Sum('current_balance'))['total'] or 0

    data = {
        'transactions': {
            'total_revenue': str(tx_stats['total_revenue'] or 0),
            'total_transactions': tx_stats['total_transactions'] or 0,
            'total_discs_granted': tx_stats['total_discs_granted'] or 0,
            'total_gems_granted': tx_stats['total_gems_granted'] or 0,
        },
        'payments': payment_breakdown,
        'payees': {
            'artists_with_balance': artists_with_balance,
            'total_outstanding': total_outstanding,
        },
    }

    return Response(data)
