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
from rest_framework.decorators import api_view, authentication_classes, permission_classes
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
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def revenue_payee_list(request):
    """
    GET /admin/revenue/payees/
    List labels as payees. Returns flat array matching AdminPayee[] type.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    from .models import Label, Song, PlayerSongInstance
    from django.db.models import Sum as DSum

    labels = Label.objects.all().order_by('name')
    results = []
    for label in labels:
        artist_ids = list(Artist.objects.filter(label=label).values_list('id', flat=True))
        artist_count = len(artist_ids)
        song_ids = list(Song.objects.filter(artist_id__in=artist_ids).values_list('id', flat=True))
        total_plays = PlayerSongInstance.objects.filter(song_id__in=song_ids).aggregate(
            tp=DSum('no_of_plays')
        )['tp'] or 0

        results.append({
            'id': label.id,
            'name': label.name,
            'artist_count': artist_count,
            'total_plays': total_plays,
        })

    return Response(results)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def revenue_payee_detail(request, pk):
    """
    GET /admin/revenue/payees/<pk>/
    Label (payee) detail with artists, payouts, and payment records.
    Returns shape matching AdminPayeeDetail frontend type.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    from .models import Label, Song, PlayerSongInstance
    label = get_object_or_404(Label, pk=pk)

    # Artists under this label
    artists = Artist.objects.filter(label=label).order_by('name')
    artists_data = []
    for a in artists:
        artist_song_ids = list(Song.objects.filter(artist=a).values_list('id', flat=True))
        song_count = len(artist_song_ids)
        total_plays = PlayerSongInstance.objects.filter(song_id__in=artist_song_ids).aggregate(
            tp=Sum('no_of_plays')
        )['tp'] or 0
        artists_data.append({
            'id': a.id,
            'name': a.name,
            'song_count': song_count,
            'total_plays': total_plays,
        })

    # Payouts for artists in this label
    artist_ids = [a.id for a in artists]
    payouts = Payout.objects.filter(artist_id__in=artist_ids).order_by('-date')
    payouts_data = []
    for p in payouts:
        payouts_data.append({
            'id': p.id,
            'amount': str(0),
            'period_start': p.date.strftime('%Y-%m-%d'),
            'period_end': p.date.strftime('%Y-%m-%d'),
            'status': 'completed',
            'created_at': p.date.isoformat(),
        })

    # Payment records for this label
    payment_records = PaymentStatus.objects.filter(
        payee_type='label', payee_id=label.id
    ).order_by('-period_year', '-period_month')
    payments_data = []
    for ps in payment_records:
        payments_data.append({
            'id': ps.id,
            'payee_name': label.name,
            'amount': str(ps.payment_amount or 0),
            'currency': 'USD',
            'status': ps.status,
            'payment_method': ps.payment_method,
            'reference': None,
            'period_start': f'{ps.period_year}-{ps.period_month:02d}-01' if ps.period_year else None,
            'period_end': f'{ps.period_year}-{ps.period_month:02d}-28' if ps.period_year else None,
            'notes': ps.notes,
            'created_at': ps.created_at.isoformat(),
            'updated_at': ps.updated_at.isoformat(),
        })

    data = {
        'label': {
            'id': label.id,
            'name': label.name,
            'is_system': label.is_system,
            'artist_count': len(artists_data),
        },
        'artists': artists_data,
        'payouts': payouts_data,
        'payments': payments_data,
    }

    return Response(data)


@api_view(['GET'])
@authentication_classes([])
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

    payments = PaymentStatus.objects.all()

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        payments = payments.filter(status=status_filter)

    payee_id = request.GET.get('payee_id', '').strip()
    if payee_id:
        payments = payments.filter(payee_id=payee_id)

    payee_type = request.GET.get('payee_type', '').strip()
    if payee_type:
        payments = payments.filter(payee_type=payee_type)

    # Pagination
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 1000)
    total = payments.count()
    start = (page - 1) * page_size
    end = start + page_size
    payments_page = payments[start:end]

    results = []
    for ps in payments_page:
        payee_name = None
        if ps.payee_type == 'artist':
            try:
                payee_name = Artist.objects.get(id=ps.payee_id).name
            except Artist.DoesNotExist:
                payee_name = f'Artist #{ps.payee_id}'

        results.append({
            'id': ps.id,
            'payee_type': ps.payee_type,
            'payee_id': ps.payee_id,
            'payee_name': payee_name,
            'period_month': ps.period_month,
            'period_year': ps.period_year,
            'payment_amount': str(ps.payment_amount or 0),
            'payment_method': ps.payment_method,
            'status': ps.status,
            'invoice_date': ps.invoice_date.isoformat() if ps.invoice_date else None,
            'payment_date': ps.payment_date.isoformat() if ps.payment_date else None,
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
@authentication_classes([])
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
    payee_type = data.get('payee_type', 'artist')
    payee_id = data.get('payee_id')
    if not payee_id:
        return Response({'error': 'payee_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    required = ['period_month', 'period_year']
    for field in required:
        if not data.get(field):
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)

    payment = PaymentStatus.objects.create(
        payee_type=payee_type,
        payee_id=payee_id,
        period_month=int(data['period_month']),
        period_year=int(data['period_year']),
        payment_amount=data.get('payment_amount'),
        payment_method=data.get('payment_method'),
        status=data.get('status', 'unpaid'),
        invoice_date=data.get('invoice_date'),
        payment_date=data.get('payment_date'),
        updated_by=admin,
        notes=data.get('notes', ''),
    )

    log_audit(
        admin_email=admin.google_email,
        action='create',
        entity_type='payment_status',
        entity_id=str(payment.id),
        changes={'payee': f'{payee_type}:{payee_id}', 'amount': str(payment.payment_amount or 0), 'status': payment.status},
        request=request,
    )

    return Response({
        'id': payment.id,
        'payee_type': payee_type,
        'payee_id': payee_id,
        'payment_amount': str(payment.payment_amount or 0),
        'status': payment.status,
        'message': 'Payment record created.',
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@authentication_classes([])
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
    if 'payment_amount' in data:
        payment.payment_amount = data['payment_amount']
    if 'payment_method' in data:
        payment.payment_method = data['payment_method']
    if 'payment_date' in data:
        payment.payment_date = data['payment_date']
    payment.updated_by = admin

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
@authentication_classes([])
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
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def revenue_summary(request):
    """
    GET /admin/revenue/summary/
    Revenue summary/overview with aggregated metrics.
    Returns flat shape matching AdminRevenueSummary frontend type.
    """
    admin = get_admin_user(request)
    if not admin:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if admin.role not in ('super_user', 'product_manager'):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)

    # Total transaction stats (all paid)
    tx_all = XsollaTransaction.objects.filter(status='paid').aggregate(
        total_revenue=Sum('amount'),
        total_transactions=Count('id'),
        total_discs_granted=Sum('discs_granted'),
        total_gems_granted=Sum('gems_granted'),
    )

    # Live vs sandbox breakdown
    tx_live = XsollaTransaction.objects.filter(status='paid', is_sandbox=False).aggregate(
        revenue=Sum('amount'),
    )
    tx_sandbox = XsollaTransaction.objects.filter(status='paid', is_sandbox=True).aggregate(
        revenue=Sum('amount'),
    )

    # Payment status breakdown
    payment_stats = PaymentStatus.objects.values('status').annotate(
        count=Count('id'),
    )
    total_payments = 0
    by_status = {}
    for ps in payment_stats:
        by_status[ps['status']] = ps['count']
        total_payments += ps['count']

    data = {
        'total_transactions': tx_all['total_transactions'] or 0,
        'total_revenue': str(tx_all['total_revenue'] or 0),
        'live_revenue': str(tx_live['revenue'] or 0),
        'sandbox_revenue': str(tx_sandbox['revenue'] or 0),
        'total_discs_granted': tx_all['total_discs_granted'] or 0,
        'total_gems_granted': tx_all['total_gems_granted'] or 0,
        'payments': {
            'total': total_payments,
            'by_status': by_status,
        },
    }

    return Response(data)
