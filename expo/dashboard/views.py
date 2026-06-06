from public.models import City, Country, Exhibition, Booking, Category, Stall, Contact, Enquiry, register as RegisterModel, UserProfile, Notification
from decimal import Decimal
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import calendar
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from django.db.models import Sum, Count, Case, When, IntegerField, F, Q
from django.db.models.functions import TruncMonth
from django.template.loader import render_to_string

# Create your views here.



# DASHBOARD
@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    
    user_reg = RegisterModel.objects.filter(user=request.user).first()
    if user_reg and user_reg.role == 'Organizer':
        return redirect('organizer_dashboard')
    else:
        return redirect('user_dashboard')
    
# ADMIN DASHBOARD
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    total_users = User.objects.count()
    total_exhibitions = Exhibition.objects.count()
    total_bookings = Booking.objects.count()
    # Combine standard contact and exhibition enquiries
    total_enquiries = Contact.objects.count() + Enquiry.objects.count()
    
    pending_organizers_count = RegisterModel.objects.filter(role='Organizer', is_approved=False).count()
    pending_exhibitions_count = Exhibition.objects.filter(status="pending").count()
    
    # Get recent pending exhibitions for the dashboard table
    recent_pending = Exhibition.objects.filter(status="pending").order_by('-created_at')[:5]
    
    # Get all exhibitions for the Platform Overview table
    all_exhibitions = Exhibition.objects.all().order_by('-created_at')[:10] # Limit to top 10 for dashboard
    for ex in all_exhibitions:
        # Booked Stalls
        ex.booked_stalls = Booking.objects.filter(
            exhibition=ex, 
            booking_type='stall'
        ).exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
        
        # Booked Tickets
        ex.booked_tickets = Booking.objects.filter(
            exhibition=ex, 
            booking_type='ticket'
        ).exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
        
        ex.available_stalls = max(0, ex.total_stalls - ex.booked_stalls)
        ex.available_tickets = max(0, ex.total_tickets - ex.booked_tickets)
        
        # Percentages
        ex.stall_percent = (ex.booked_stalls / ex.total_stalls * 100) if ex.total_stalls > 0 else 0
        ex.ticket_percent = (ex.booked_tickets / ex.total_tickets * 100) if ex.total_tickets > 0 else 0

    # Calculate global stall and ticket stats for Admin

    total_stalls_capacity = Exhibition.objects.filter(status='approved').aggregate(Sum('total_stalls'))['total_stalls__sum'] or 0
    total_tickets_capacity = Exhibition.objects.filter(status='approved').aggregate(Sum('total_tickets'))['total_tickets__sum'] or 0
    
    total_stalls_booked = Booking.objects.filter(booking_type='stall').exclude(status='cancelled').aggregate(Sum('stalls'))['stalls__sum'] or 0
    total_tickets_sold = Booking.objects.filter(booking_type='ticket').exclude(status='cancelled').aggregate(Sum('stalls'))['stalls__sum'] or 0

    # Get recent enquiries (Both types)
    from django.db.models import Value, CharField
    contact_enq = Contact.objects.annotate(type=Value('general', output_field=CharField())).values('id', 'subject', 'message', 'created_at', 'type')
    exhib_enq = Enquiry.objects.annotate(type=Value('exhibition', output_field=CharField())).values('id', 'subject', 'message', 'created_at', 'type')
    
    from itertools import chain
    all_enq = sorted(chain(contact_enq, exhib_enq), key=lambda x: x['created_at'], reverse=True)
    recent_enquiries = all_enq[:6] # Top 6 recent across both types

    # Get recent notifications
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    # --- CHART DATA FOR ADMIN ---
    # 1. Monthly Revenue Trends (Jan to Dec of Current Year)
    current_year = timezone.now().year
    chart_labels = [calendar.month_name[i][:3] for i in range(1, 13)] # ['Jan', 'Feb', ..., 'Dec']
    chart_data = []
    
    for i in range(1, 13):
        # Calculate revenue for each specific month in the current year
        month_revenue = Booking.objects.filter(
            created_at__year=current_year,
            created_at__month=i,
            payment_status='completed'
        ).aggregate(total=Sum('total_price'))['total'] or 0
        chart_data.append(float(month_revenue))

    # 2. Category Distribution (Revenue)
    revenue_by_cat = Category.objects.annotate(
        revenue=Sum(Case(
            When(exhibition__booking__payment_status='completed', then='exhibition__booking__total_price'),
            default=Decimal('0'),
            output_field=IntegerField()
        ))
    ).values('name', 'revenue')
    
    rev_cat_labels = [c['name'] for c in revenue_by_cat if c['revenue'] > 0]
    rev_cat_values = [float(c['revenue']) for c in revenue_by_cat if c['revenue'] > 0]

    # 3. User Growth Trends (Jan to Dec of Current Year)
    user_trend_labels = chart_labels # Matches Jan-Dec
    user_trend_data = []
    for i in range(1, 13):
        user_count = User.objects.filter(
            date_joined__year=current_year,
            date_joined__month=i
        ).count()
        user_trend_data.append(user_count)

    # Get recent bookings (Any type) for the global overview
    recent_bookings = Booking.objects.all().select_related('user', 'exhibition', 'exhibition__user').order_by('-created_at')[:10]

    # --- ADVANCED STATS ---
    # 1. Total Revenue (Completed only)
    total_revenue = Booking.objects.filter(payment_status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # 2. 24-Hour Growth Stats
    one_day_ago = timezone.now() - timedelta(days=1)
    new_users_24h = User.objects.filter(date_joined__gte=one_day_ago).count()
    new_bookings_24h = Booking.objects.filter(created_at__gte=one_day_ago).count()
    
    # Clean up redundant/moved code
    
    # 4. Recent Active Users
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    for u in recent_users:
        u.reg = RegisterModel.objects.filter(user=u).first()

    # 5. Type Distribution (Stalls vs Tickets)
    type_data = Booking.objects.values('booking_type').annotate(count=Count('id'))
    type_labels = [t['booking_type'].capitalize() for t in type_data]
    type_values = [t['count'] for t in type_data]

    # AJAX Polling Support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'stats': {
                'total_revenue': float(total_revenue),
                'total_users': total_users,
                'pending_tasks': pending_exhibitions_count + pending_organizers_count,
                'total_exhibitions': total_exhibitions,
                'total_stalls_booked': total_stalls_booked,
                'total_stalls_capacity': total_stalls_capacity,
                'total_tickets_sold': total_tickets_sold,
                'total_tickets_capacity': total_tickets_capacity,
                'total_bookings': total_bookings,
                'new_users_24h': new_users_24h,
                'new_bookings_24h': new_bookings_24h,
            },
            'charts': {
                'revenue_trend': {'labels': chart_labels, 'values': chart_data},
                'user_trend': {'labels': user_trend_labels, 'values': user_trend_data},
                'category_dist': {'labels': rev_cat_labels, 'values': rev_cat_values},
            }
        })

    context = {
        "total_users": total_users,
        "total_exhibitions": total_exhibitions,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "new_users_24h": new_users_24h,
        "new_bookings_24h": new_bookings_24h,
        "rev_cat_labels": rev_cat_labels,
        "rev_cat_values": rev_cat_values,
        "user_trend_labels": user_trend_labels,
        "user_trend_data": user_trend_data,
        "recent_users": recent_users,
        "type_labels": type_labels,
        "type_values": type_values,
        "total_stalls_capacity": total_stalls_capacity,
        "total_tickets_capacity": total_tickets_capacity,
        "total_stalls_booked": total_stalls_booked,
        "total_tickets_sold": total_tickets_sold,
        "total_enquiries": total_enquiries,
        "pending_organizers_count": pending_organizers_count,
        "pending_exhibitions_count": pending_exhibitions_count,
        "recent_pending": recent_pending,
        "all_exhibitions": all_exhibitions,
        "recent_bookings": recent_bookings,
        "recent_enquiries": recent_enquiries,
        "recent_notifications": recent_notifications,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }

    return render(request, 'admin_dashboard.html', context)

# USER DASHBOARD
@login_required
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    user_reg = RegisterModel.objects.filter(user=request.user).first()
    role = user_reg.role if user_reg else 'Visitor'

    if role == 'Organizer':
        return redirect('organizer_dashboard')

    my_bookings_count = Booking.objects.filter(user=request.user).count()
    recent_bookings = Booking.objects.filter(user=request.user).order_by('-created_at')[:5]

    # Get recent notifications
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    # Get user enquiries
    user_enquiries_list = Enquiry.objects.filter(user=request.user).order_by('-created_at')[:5]
    user_enquiries_count = Enquiry.objects.filter(user=request.user).count()

    # --- CHART DATA FOR USER ---
    # Booking Type Distribution
    stall_count = Booking.objects.filter(user=request.user, booking_type='stall').count()
    ticket_count = Booking.objects.filter(user=request.user, booking_type='ticket').count()

    context = {
        "role": role,
        "my_bookings_count": my_bookings_count,
        "recent_bookings": recent_bookings,
        "recent_notifications": recent_notifications,
        "my_enquiries_count": user_enquiries_count,
        "recent_enquiries": user_enquiries_list,
        "chart_data": [stall_count, ticket_count],
        "chart_labels": ["Stalls", "Tickets"],
    }

    return render(request, 'user_dashboard.html', context)

@login_required
def organizer_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    user_reg = RegisterModel.objects.filter(user=request.user).first()
    
    if not user_reg or user_reg.role != 'Organizer':
        return redirect('user_dashboard')

    # Check if organizer is approved
    if not user_reg.is_approved:
        return render(request, 'organizer_dashboard.html', {"role": 'Organizer', "is_approved": False})
        
    my_exhibitions = Exhibition.objects.filter(user=request.user).order_by('-created_at')
    my_exhibitions_count = my_exhibitions.count()
    
    # Global Bookings for this Organizer
    my_bookings = Booking.objects.filter(exhibition__user=request.user)
    total_bookings = my_bookings.count()
    total_revenue = my_bookings.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or 0
    
    # Stall vs Ticket Counts (Doughnut Chart)
    stalls_count = my_bookings.filter(booking_type='stall').count()
    tickets_count = my_bookings.filter(booking_type='ticket').count()
    
    # Global Stall & Ticket Capacity
    total_stalls_capacity = my_exhibitions.aggregate(total=Sum('total_stalls'))['total'] or 0
    total_tickets_capacity = my_exhibitions.aggregate(total=Sum('total_tickets'))['total'] or 0
    
    total_stalls_booked = my_bookings.filter(booking_type='stall').exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
    total_tickets_sold = my_bookings.filter(booking_type='ticket').exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
    
    stall_usage_percent = (total_stalls_booked / total_stalls_capacity * 100) if total_stalls_capacity > 0 else 0
    ticket_usage_percent = (total_tickets_sold / total_tickets_capacity * 100) if total_tickets_capacity > 0 else 0

    # Growth & New Data (Last 24h)
    total_customers = my_bookings.values('user').distinct().count()
    new_bookings_24h = my_bookings.filter(created_at__gte=timezone.now() - timedelta(days=1)).count()
    
    # Recent Bookings for Table
    recent_bookings = my_bookings.select_related('user', 'exhibition').order_by('-created_at')[:5]

    # Recent Notifications
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    # --- ADVANCED CHART DATA ---
    # Trend Data (Last 14 Days for "Live" feel)
    trend_labels = []
    trend_values = []
    for i in range(13, -1, -1):
        day_date = timezone.now() - timedelta(days=i)
        day_label = day_date.strftime('%d %b')
        day_bookings = my_bookings.filter(created_at__date=day_date.date()).count()
        trend_labels.append(day_label)
        trend_values.append(day_bookings)

    # Performance per Exhibition (for Bar/Pie Charts)
    exhibition_stats = my_exhibitions.annotate(
        bookings_count=Count('booking'),
        revenue=Sum('booking__total_price')
    )[:10]
    
    org_labels = [ex.title for ex in exhibition_stats]
    org_bookings = [ex.bookings_count for ex in exhibition_stats]
    org_revenue = [float(ex.revenue or 0) for ex in exhibition_stats]

    recent_enquiries = Enquiry.objects.filter(exhibition__user=request.user).order_by('-created_at')[:5]
    pending_enquiries_count = Enquiry.objects.filter(exhibition__user=request.user).count()

    # --- EXHIBITION HEALTH METRICS ---
    active_exhibitions = Exhibition.objects.filter(user=request.user).order_by('-created_at')[:4]
    exhibition_health = []
    today = timezone.now().date()
    
    for ex in active_exhibitions:
        ex_bookings = Booking.objects.filter(exhibition=ex).exclude(status='cancelled')
        stalls_booked = ex_bookings.filter(booking_type='stall').aggregate(total=Sum('stalls'))['total'] or 0
        occupancy_percent = round((stalls_booked / ex.total_stalls * 100), 1) if ex.total_stalls > 0 else 0
        actual_revenue = ex_bookings.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or 0
        
        days_to_go = (ex.start_date - today).days if ex.start_date else None
        if days_to_go is not None: days_to_go = max(0, days_to_go)

        exhibition_health.append({
            'exhibition': ex,
            'occupancy_percent': occupancy_percent,
            'actual_revenue': float(actual_revenue),
            'days_to_go': days_to_go,
        })

    # AJAX Polling Support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'stats': {
                'total_revenue': float(total_revenue),
                'total_bookings': total_bookings,
                'my_exhibitions_count': my_exhibitions_count,
                'total_stalls_booked': total_stalls_booked,
                'total_stalls_capacity': total_stalls_capacity,
                'total_tickets_sold': total_tickets_sold,
                'total_tickets_capacity': total_tickets_capacity,
                'new_bookings_24h': new_bookings_24h,
                'pending_enquiries_count': pending_enquiries_count,
            },
            'charts': {
                'revenue': {'labels': trend_labels, 'values': trend_values},
                'distribution': {'labels': ['Stalls', 'Tickets'], 'values': [stalls_count, tickets_count]},
                'exhibition_revenue': {'labels': org_labels, 'values': org_revenue}
            },
            'health_html': render_to_string('dashboard/partials/exhibition_health.html', {'exhibition_health': exhibition_health})
        })

    context = {
        "role": 'Organizer',
        "is_approved": True,
        "my_exhibitions_count": my_exhibitions_count,
        "total_bookings": total_bookings,
        "total_revenue": float(total_revenue),
        "total_stalls_capacity": total_stalls_capacity,
        "total_stalls_booked": total_stalls_booked,
        "total_tickets_capacity": total_tickets_capacity,
        "total_tickets_sold": total_tickets_sold,
        "stall_usage_percent": round(stall_usage_percent, 1),
        "ticket_usage_percent": round(ticket_usage_percent, 1),
        "new_bookings_24h": new_bookings_24h,
        "pending_enquiries_count": pending_enquiries_count,
        "my_exhibitions": my_exhibitions[:5],
        "recent_bookings": recent_bookings,
        "recent_notifications": recent_notifications,
        "recent_enquiries": recent_enquiries,
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "type_labels": ["Stalls", "Tickets"],
        "type_values": [stalls_count, tickets_count],
        "exhibition_health": exhibition_health,
        "org_labels": org_labels,
        "org_bookings": org_bookings,
        "org_revenue": org_revenue,
        "recent_enquiries": recent_enquiries,
    }

    return render(request, 'organizer_dashboard.html', context)

# ... (rest of existing views) ...

# LIST ORGANIZERS (Admin Only)
@login_required
@staff_member_required
def list_organizers(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
    
    # Show pending organizer signups AND visitor-to-organizer upgrade requests
    organizers = RegisterModel.objects.filter(
        Q(role='Organizer') | Q(role_upgrade_pending=True)
    ).order_by('-role_upgrade_pending', 'is_approved', '-created_at')
    
    return render(request, "approve_organizers.html", {"organizers": organizers})

# APPROVE ORGANIZER / UPGRADE (Admin Only)
@login_required
@staff_member_required
def approve_organizer(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    reg = get_object_or_404(RegisterModel, id=id)
    is_upgrade = reg.role_upgrade_pending
    
    if is_upgrade:
        reg.role = 'Organizer'
        reg.role_upgrade_pending = False
    
    reg.is_approved = True
    reg.save()
    
    # Notify User Email
    from public.email_utils import send_organizer_approval_email
    send_organizer_approval_email(reg, 'approved')
    
    # Notify User (In-App)
    title = "Account Upgraded" if is_upgrade else "Account Approved"
    message = "Your account has been upgraded to Organizer." if is_upgrade else "Your organizer account has been approved."
    
    Notification.objects.create(
        user=reg.user,
        title=title,
        message=message + " You can now create and manage exhibitions.",
        notification_type='organizer',
        link="/dashboard/organizer_dashboard/"
    )
    
    messages.success(request, f"Request for '{reg.full_name}' approved successfully.")
    return redirect('list_organizers')

# REJECT ORGANIZER / UPGRADE (Admin Only)
@login_required
@staff_member_required
def reject_organizer(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    reg = get_object_or_404(RegisterModel, id=id)
    user = reg.user
    is_upgrade = reg.role_upgrade_pending
    
    if is_upgrade:
        reg.role_upgrade_pending = False
        reg.save()
        # Notify for upgrade rejection
        Notification.objects.create(
            user=user,
            title="Organizer Request Declined",
            message="Your request to become an organizer has been declined. You can still browse and book as a visitor.",
            notification_type='visitor',
            link="/dashboard/user_dashboard/"
        )
        messages.warning(request, "Role upgrade request rejected.")
    else:
        # Standard rejection for new signups
        from public.email_utils import send_organizer_approval_email
        send_organizer_approval_email(reg, 'rejected')
        
        Notification.objects.create(
            user=user,
            title="Organizer Request Declined",
            message="Your request to become an organizer has been declined. You can still browse and book as a visitor.",
            notification_type='visitor',
            link="/dashboard/user_dashboard/"
        )
        reg.delete() 
        messages.warning(request, "Organizer request rejected.")

    return redirect('list_organizers')

# REQUEST ORGANIZER UPGRADE (Visitor Only)
@login_required
def request_organizer_upgrade(request):
    reg = RegisterModel.objects.filter(user=request.user).first()
    if not reg or reg.role != 'Visitor':
        messages.error(request, "Invalid request.")
        return redirect('dashboard_redirect')
    
    if reg.role_upgrade_pending:
        messages.info(request, "Your request is already pending approval.")
        return redirect('user_dashboard')

    if request.method == 'POST':
        # Check if terms were accepted
        if request.POST.get('terms_accepted') != 'on':
            messages.error(request, "You must accept the Terms & Conditions to proceed.")
            return redirect('request_organizer_upgrade')

        reg.role_upgrade_pending = True
        reg.save()
        
        # Notify Admins
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="New Role Upgrade Request",
                message=f"Visitor {reg.full_name} has requested to become an Organizer.",
                notification_type='admin',
                link="/dashboard/organizers/"
            )
            
        messages.success(request, "Your request to become an Organizer has been submitted. You will be notified once approved.")
        return redirect('user_dashboard')
        
    return render(request, "request_organizer.html", {"register": reg})

# MY BOOKINGS
@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    stall_bookings_count = bookings.filter(booking_type='stall').count()
    ticket_bookings_count = bookings.filter(booking_type='ticket').count()
    total_spent = bookings.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or 0
    
    context = {
        'bookings': bookings,
        'stall_bookings_count': stall_bookings_count,
        'ticket_bookings_count': ticket_bookings_count,
        'total_spent': total_spent,
    }
    return render(request, 'my_bookings.html', context)

# MY EXHIBITION BOOK
@login_required
def my_exhibition_book(request, ex_id=None):
    # Base queryset: bookings for exhibitions owned by the user
    bookings = Booking.objects.filter(exhibition__user=request.user)
    
    current_exhibition = None
    if ex_id:
        current_exhibition = get_object_or_404(Exhibition, id=ex_id, user=request.user)
        bookings = bookings.filter(exhibition=current_exhibition)
    
    # Filter by Booking Type
    booking_type = request.GET.get('type')
    if booking_type in ['ticket', 'stall']:
        bookings = bookings.filter(booking_type=booking_type)
        
    bookings = bookings.order_by('-created_at')
    
    # Calculate Summary Stats for the current view
    total_bookings = bookings.count()
    # Filter for active (not cancelled) bookings for revenue
    active_bookings = bookings.exclude(status='cancelled')
    total_revenue = active_bookings.aggregate(total=Sum('total_price'))['total'] or 0
    total_stalls = active_bookings.filter(booking_type='stall').aggregate(total=Sum('stalls'))['total'] or 0
    total_tickets = active_bookings.filter(booking_type='ticket').aggregate(total=Sum('stalls'))['total'] or 0
    pending_count = bookings.filter(status='pending').count()
    
    # Get all user's exhibitions for the filter dropdown
    user_exhibitions = Exhibition.objects.filter(user=request.user).order_by('title')
    
    context = {
        'bookings': bookings,
        'stall_bookings': bookings.filter(booking_type='stall'),
        'ticket_bookings': bookings.filter(booking_type='ticket'),
        'current_exhibition': current_exhibition,
        'user_exhibitions': user_exhibitions,
        'stats': {
            'total_bookings': total_bookings,
            'total_revenue': float(total_revenue),
            'total_stalls': total_stalls,
            'total_tickets': total_tickets,
            'pending_count': pending_count,
        }
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'stats': context['stats'],
            'bookings_html': render_to_string('dashboard/partials/booking_rows.html', {'bookings': bookings})
        })

    return render(request, 'my_exhibition_book.html', context)

@login_required
def download_exhibition_book_pdf(request, ex_id=None):
    # Base queryset: bookings for exhibitions owned by the user
    bookings = Booking.objects.filter(exhibition__user=request.user)
    
    current_exhibition = None
    title = "All Exhibitions Summary"
    if ex_id:
        current_exhibition = get_object_or_404(Exhibition, id=ex_id, user=request.user)
        bookings = bookings.filter(exhibition=current_exhibition)
        title = f"Exhibition Summary: {current_exhibition.title}"
    
    # Filter by Booking Type
    booking_type = request.GET.get('type')
    if booking_type in ['ticket', 'stall']:
        bookings = bookings.filter(booking_type=booking_type)
        title += f" ({booking_type.capitalize()}s Only)"
        
    bookings = bookings.order_by('-created_at')
    
    # Generate PDF using utility
    from public.utils import generate_exhibition_summary_pdf
    buffer = generate_exhibition_summary_pdf(bookings, title)
    
    filename = f"Exhibition_Report_{timezone.now().strftime('%Y%m%d')}.pdf"
    if current_exhibition:
        filename = f"{current_exhibition.title.replace(' ', '_')}_Report.pdf"
        
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def update_booking_status(request, id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=id)
        if booking.exhibition.user != request.user and not request.user.is_superuser:
            messages.error(request, "Permission denied.")
            return redirect('my_exhibition_book')
        
        status = request.POST.get('status')
        if status in dict(Booking.BOOKING_STATUS_CHOICES):
            booking.status = status
            booking.save()
            
            # Send Notification Email
            from public.email_utils import send_booking_email
            send_booking_email(booking, status)
            
            # Notify Visitor (In-app)
            Notification.objects.create(
                user=booking.user,
                title=f"Booking {status.title()}",
                message=f"Your booking for '{booking.exhibition.title}' has been {status}.",
                notification_type='visitor',
                link="/dashboard/my-bookings/"
            )
            
            messages.success(request, f"Booking status updated to {booking.get_status_display()}. Email notification sent.")
    
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('my_exhibition_book')

@login_required
def update_payment_status(request, id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=id)
        if booking.exhibition.user != request.user and not request.user.is_superuser:
            messages.error(request, "Permission denied.")
            return redirect('my_exhibition_book')
            
        payment_status = request.POST.get('payment_status')
        if payment_status in dict(Booking.PAYMENT_STATUS_CHOICES):
            booking.payment_status = payment_status
            booking.save()
            
            # Notify Visitor
            Notification.objects.create(
                user=booking.user,
                title=f"Payment {payment_status.title()}",
                message=f"Payment for your booking at '{booking.exhibition.title}' is now {payment_status}.",
                notification_type='visitor',
                link="/dashboard/my-bookings/"
            )
            
            messages.success(request, f"Payment status for {booking.user.username} updated to {booking.get_payment_status_display()}.")
            
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('my_exhibition_book')

@login_required
def my_enquiries(request):
    # Fetch enquiries for exhibitions created by the current user
    enquiries = Enquiry.objects.filter(exhibition__user=request.user).order_by('-created_at')
    return render(request, 'my_enquiries.html', {'enquiries': enquiries})

@login_required
def respond_enquiry(request, id):
    if request.method == "POST":
        enquiry = get_object_or_404(Enquiry, id=id)
        if enquiry.exhibition.user != request.user and not request.user.is_superuser:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Permission denied.'})
            messages.error(request, "Permission denied.")
            return redirect('my_enquiries')
        
        reply_message = request.POST.get('reply')
        if reply_message:
            enquiry.reply = reply_message
            enquiry.is_replied = True
            enquiry.save()
            
            # Notify User (In-app)
            Notification.objects.create(
                user=enquiry.user,
                title="Enquiry Responded",
                message=f"The organizer has responded to your enquiry regarding '{enquiry.exhibition.title}'.",
                notification_type='visitor',
                link="/dashboard/enquiries/"
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Response sent successfully.',
                    'reply': enquiry.reply
                })
                
            messages.success(request, "Response sent successfully.")
    
    return redirect('my_enquiries')

# USER ENQUIRIES (Sent/Inbox)
@login_required
def user_enquiries(request):
    # Fetch enquiries sent by the current user
    enquiries = Enquiry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'enquiries.html', {'enquiries': enquiries})

@login_required
def admin_enquiries(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    enquiries = Contact.objects.all().order_by('-created_at')
    
    # AJAX filtering for live dynamic response
    filter_type = request.GET.get('filter')
    if filter_type == 'pending':
        enquiries = enquiries.filter(is_replied=False)
    elif filter_type == 'replied':
        enquiries = enquiries.filter(is_replied=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'enquiries_html': render_to_string('dashboard/partials/admin_enquiries_rows.html', {'enquiries': enquiries}),
            'stats': {
                'total': Contact.objects.count(),
                'pending': Contact.objects.filter(is_replied=False).count(),
                'replied': Contact.objects.filter(is_replied=True).count(),
            }
        })

    context = {
        'enquiries': enquiries,
        'stats': {
            'total': Contact.objects.count(),
            'pending': Contact.objects.filter(is_replied=False).count(),
            'replied': Contact.objects.filter(is_replied=True).count(),
        }
    }
    return render(request, 'admin_enquiries.html', context)

@login_required
def respond_admin_enquiry(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    if request.method == "POST":
        enquiry = get_object_or_404(Contact, id=id)
        reply_message = request.POST.get('reply')
        
        if reply_message:
            enquiry.reply = reply_message
            enquiry.is_replied = True
            enquiry.save()
            
            messages.success(request, "Response recorded successfully. The user will be notified directly.")
            
    return redirect('admin_enquiries')

@login_required
def admin_bookings(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    bookings = Booking.objects.all().select_related('user', 'exhibition', 'stall_instance', 'exhibition__user').order_by('-created_at')

    # Allow dynamic filtering via GET parameters
    ex_id = request.GET.get('exhibition')
    booking_type = request.GET.get('type')

    if ex_id and ex_id != 'all':
        bookings = bookings.filter(exhibition_id=ex_id)
        
    if booking_type and booking_type in ['stall', 'ticket']:
        bookings = bookings.filter(booking_type=booking_type)

    all_exhibitions = Exhibition.objects.all().order_by('title')

    # Calculate dynamic stats based on filtered queryset
    stats = {
        'total_bookings': bookings.count(),
        'total_stalls': bookings.filter(booking_type='stall').aggregate(total=Sum('stalls'))['total'] or 0,
        'total_tickets': bookings.filter(booking_type='ticket').aggregate(total=Sum('stalls'))['total'] or 0,
        'total_exhibitions': bookings.values('exhibition').distinct().count(),
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'bookings_html': render_to_string('dashboard/partials/admin_bookings_rows.html', {'bookings': bookings}),
            'stats': stats
        })

    return render(request, 'admin_bookings.html', {
        'bookings': bookings,
        'all_exhibitions': all_exhibitions,
        'current_exhibition_id': ex_id,
        'current_type': booking_type,
        'stats': stats
    })

@login_required
def admin_stalls(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    bookings = Booking.objects.filter(booking_type='stall', stall_instance__isnull=False).select_related('user', 'exhibition', 'stall_instance', 'exhibition__user').order_by('-created_at')
    
    ex_id = request.GET.get('exhibition')
    if ex_id and ex_id != 'all':
        bookings = bookings.filter(exhibition_id=ex_id)
        
    all_exhibitions = Exhibition.objects.all().order_by('title')
    
    # Calculate dynamic stats
    stats = {
        'total_allocations': bookings.count(),
        'total_exhibitions': bookings.values('exhibition').distinct().count(),
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'bookings_html': render_to_string('dashboard/partials/admin_stalls_rows.html', {'bookings': bookings}),
            'stats': stats
        })

    return render(request, 'admin_stalls.html', {
        'bookings': bookings,
        'all_exhibitions': all_exhibitions,
        'current_exhibition_id': ex_id,
        'stats': stats
    })

# ADD EXHIBITION PAGE
@login_required
def add_exhibition(request):

    countries = Country.objects.all()

    if request.method == "POST":

        title = request.POST.get('title')
        image = request.FILES.get('image')
        description = request.POST.get('description')
        category = request.POST.get('category')
        venue = request.POST.get('venue')
        country_id = request.POST.get('country')
        city_id = request.POST.get('city')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        ticket_price = request.POST.get('ticket_price')
        stall_price = request.POST.get('stall_price')
        total_stalls = request.POST.get('total_stalls')
        total_tickets = request.POST.get('total_tickets', 0)

        country = Country.objects.get(id=country_id)
        city = City.objects.get(id=city_id)
        category = Category.objects.get(id=category)

        Exhibition.objects.create(
            user=request.user,
            title=title,
            image=image,
            description=description,
            category=category,
            venue=venue,
            country=country,
            city=city,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            ticket_price=ticket_price,
            stall_price=stall_price,
            total_stalls=total_stalls,
            total_tickets=total_tickets,
            status="pending"   # Admin will approve
        )

        superusers = User.objects.filter(is_superuser=True)
        for admin in superusers:
            Notification.objects.create(
                user=admin,
                title="New Exhibition Request",
                message=f"New exhibition '{title}' submitted by '{request.user.username}' for approval.",
                notification_type='admin',
                link="/dashboard/approve_requests/"
            )

        messages.success(request, "Exhibition added successfully. Waiting for Admin approval.")
        return redirect('list_exhibition')

    context = {
        "countries": countries,
        "categories": Category.objects.all()
    }

    return render(request, "add_exhibition.html", context)

# LIST EXHIBITIONS
@login_required
def list_exhibition(request):
    if request.user.is_superuser:
        # Admin sees pending exhibitions to approve
        exhibitions = Exhibition.objects.all().order_by('-created_at')
    else:
        # User sees their own exhibitions
        exhibitions = Exhibition.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate live stats for each exhibition for the listing
    for ex in exhibitions:
        # Booked Stalls
        ex.booked_stalls = Booking.objects.filter(
            exhibition=ex, 
            booking_type='stall'
        ).exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
        
        # Booked Tickets
        ex.booked_tickets = Booking.objects.filter(
            exhibition=ex, 
            booking_type='ticket'
        ).exclude(status='cancelled').aggregate(total=Sum('stalls'))['total'] or 0
        
        ex.available_stalls = max(0, ex.total_stalls - ex.booked_stalls)
        ex.available_tickets = max(0, ex.total_tickets - ex.booked_tickets)
        
        # Percentages for progress bars
        ex.stall_percent = (ex.booked_stalls / ex.total_stalls * 100) if ex.total_stalls > 0 else 0
        ex.ticket_percent = (ex.booked_tickets / ex.total_tickets * 100) if ex.total_tickets > 0 else 0
    
    return render(request, "list_exhibitions.html", {"exhibitions": exhibitions})

@login_required
def stall_management_list(request):
    user_reg = RegisterModel.objects.filter(user=request.user).first()
    if not user_reg or user_reg.role != 'Organizer':
        return redirect('user_dashboard')
    
    exhibitions = Exhibition.objects.filter(user=request.user).order_by('-created_at')
    
    # Add stats for each exhibition for the listing
    for ex in exhibitions:
        ex.booked_count = ex.stalls_list.filter(status='booked').count()
        ex.available_count = ex.stalls_list.filter(status='available').count()
        ex.maint_count = ex.stalls_list.filter(status='maintenance').count()
        
    return render(request, 'stall_management_list.html', {'exhibitions': exhibitions, 'role': 'Organizer'})

# EDIT EXHIBITION
@login_required
def edit_exhibition(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)
    
    # Check permission (User only edits their own, Admin can edit anything if needed)
    if not request.user.is_superuser and exhibition.user != request.user:
        messages.error(request, "You don't have permission to edit this exhibition.")
        return redirect('list_exhibition')

    countries = Country.objects.all()
    cities = City.objects.filter(country=exhibition.country)

    if request.method == "POST":
        exhibition.title = request.POST.get('title')
        if request.FILES.get('image'):
            exhibition.image = request.FILES.get('image')
        exhibition.description = request.POST.get('description')
        category_id = request.POST.get('category')
        exhibition.venue = request.POST.get('venue')
        
        country_id = request.POST.get('country')
        city_id = request.POST.get('city')
        exhibition.country = Country.objects.get(id=country_id)
        exhibition.city = City.objects.get(id=city_id)
        exhibition.category = Category.objects.get(id=category_id)
        
        exhibition.start_date = request.POST.get('start_date')
        exhibition.end_date = request.POST.get('end_date')
        exhibition.start_time = request.POST.get('start_time')
        exhibition.end_time = request.POST.get('end_time')
        exhibition.ticket_price = request.POST.get('ticket_price')
        exhibition.stall_price = request.POST.get('stall_price')
        exhibition.total_stalls = request.POST.get('total_stalls')
        exhibition.total_tickets = request.POST.get('total_tickets', 0)
        exhibition.total_tickets = request.POST.get('total_tickets', 0)
        
        # When edited, reset status to pending for re-approval ONLY if not already approved
        if exhibition.status != "approved":
            exhibition.status = "pending"
            exhibition.is_approved = False
            
        exhibition.save()

        messages.success(request, "Exhibition updated successfully.")
        return redirect('list_exhibition')

    context = {
        "exhibition": exhibition,
        "countries": countries,
        "cities": cities,
        "categories": Category.objects.all()
    }
    return render(request, "edit_exhibition.html", context)

@login_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Ensure the person deleting is the organizer of the exhibition
    if booking.exhibition.user != request.user: # Changed from organizer to user based on Exhibition model
        from django.http import HttpResponseForbidden # Import needed
        return HttpResponseForbidden("You are not authorized to delete this booking.")
    
    booking.delete()
    return redirect('my_exhibition_book') # Assuming 'my_exhibition_book' is the correct redirect

@login_required
def stall_bookings(request):
    user_exhibitions = Exhibition.objects.filter(user=request.user) # Changed from organizer to user
    bookings = Booking.objects.filter(exhibition__in=user_exhibitions, booking_type='stall').order_by('-created_at')
    
    # Calculate stats for stalls only
    from django.db.models import Sum # Import needed
    total_revenue = bookings.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or 0
    total_stalls = bookings.aggregate(total=Sum('stalls'))['total'] or 0
    pending_count = bookings.filter(status='pending').count()
    
    stats = {
        'total_bookings': bookings.count(),
        'total_revenue': float(total_revenue),
        'total_stalls': total_stalls,
        'total_tickets': 0,
        'pending_count': pending_count
    }
    
    context = {
        'bookings': bookings,
        'stats': stats,
        'user_exhibitions': user_exhibitions,
        'current_type': 'Stall'
    }
    return render(request, 'my_exhibition_book.html', context)

@login_required
def ticket_bookings(request):
    user_exhibitions = Exhibition.objects.filter(user=request.user) # Changed from organizer to user
    bookings = Booking.objects.filter(exhibition__in=user_exhibitions, booking_type='ticket').order_by('-created_at')
    
    # Calculate stats for tickets only
    from django.db.models import Sum # Import needed
    total_revenue = bookings.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or 0
    total_tickets = bookings.aggregate(total=Sum('stalls'))['total'] or 0
    pending_count = bookings.filter(status='pending').count()
    
    stats = {
        'total_bookings': bookings.count(),
        'total_revenue': float(total_revenue),
        'total_stalls': 0,
        'total_tickets': total_tickets,
        'pending_count': pending_count
    }
    
    context = {
        'bookings': bookings,
        'stats': stats,
        'user_exhibitions': user_exhibitions,
        'current_type': 'Ticket'
    }
    return render(request, 'my_exhibition_book.html', context)

# DELETE EXHIBITION
@login_required
def delete_exhibition(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)
    
    # Check permission
    if not request.user.is_superuser and exhibition.user != request.user:
        messages.error(request, "You don't have permission to delete this exhibition.")
        return redirect('list_exhibition')
        
    exhibition.delete()
    messages.success(request, "Exhibition deleted successfully.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('list_exhibition')

# APPROVE EXHIBITION (Admin Only)
@login_required
@staff_member_required
def approve_exhibition(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    exhibition = get_object_or_404(Exhibition, id=id)
    exhibition.status = "approved"
    exhibition.is_approved = True
    exhibition.save()
    
    # Notify Organizer Email
    from public.email_utils import send_exhibition_approval_email
    send_exhibition_approval_email(exhibition, 'approved')
    
    # In-App Notification
    Notification.objects.create(
        user=exhibition.user,
        title="Exhibition Approved",
        message=f"Your exhibition '{exhibition.title}' has been approved and is now live.",
        notification_type='organizer',
        link="/dashboard/list/"
    )
    
    messages.success(request, f"Exhibition '{exhibition.title}' approved successfully.")
    return redirect('approve_requests')

# REJECT EXHIBITION (Admin Only)
@login_required
@staff_member_required
def reject_exhibition(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    exhibition = get_object_or_404(Exhibition, id=id)
    exhibition.status = "rejected"
    exhibition.is_approved = False
    exhibition.save()
    
    # Notify Organizer Email
    from public.email_utils import send_exhibition_approval_email
    send_exhibition_approval_email(exhibition, 'rejected')
    
    # In-App Notification
    Notification.objects.create(
        user=exhibition.user,
        title="Exhibition Rejected",
        message=f"Your exhibition '{exhibition.title}' was rejected. Please check requirements.",
        notification_type='organizer',
        link="/dashboard/list/"
    )
    
    messages.warning(request, f"Exhibition '{exhibition.title}' rejected.")
    return redirect('approve_requests') # Redirect to dedicated page

# DEDICATED ADMIN APPROVAL PAGE
@login_required
@staff_member_required
def approve_requests(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')

    # Sort by status (pending first) and then updated_at descending
    exhibitions = Exhibition.objects.all().order_by(
        Case(When(status='pending', then=0), default=1),
        '-updated_at'
    )
    return render(request, "approve_exhibitions.html", {"exhibitions": exhibitions})

# MANAGE CATEGORIES (Admin Only)
@login_required
@staff_member_required
def manage_categories(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
    
    categories = Category.objects.annotate(exhibition_count=Count('exhibition')).order_by('name')
    popular_cat = categories.order_by('-exhibition_count').first()
    
    if request.method == "POST":
        name = request.POST.get('name')
        icon = request.POST.get('icon', 'category')
        id = request.POST.get('id')
        
        if id: # Edit
            cat = get_object_or_404(Category, id=id)
            cat.name = name
            cat.icon = icon
            cat.save()
            messages.success(request, f"Category '{name}' updated successfully.")
        else: # Add
            Category.objects.create(name=name, icon=icon)
            messages.success(request, f"Category '{name}' added successfully.")
            
        return redirect('manage_categories')
        
    return render(request, "manage_categories.html", {
        "categories": categories,
        "popular_cat": popular_cat
    })

# DELETE CATEGORY
@login_required
@staff_member_required
def delete_category(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    cat = get_object_or_404(Category, id=id)
    name = cat.name
    cat.delete()
    messages.warning(request, f"Category '{name}' deleted successfully.")
    return redirect('manage_categories')

# MANAGE LOCATIONS (Admin Only)
@login_required
@staff_member_required
def manage_locations(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
    
    countries = Country.objects.all().order_by('name')
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "add_country":
            name = request.POST.get('name')
            Country.objects.create(name=name)
            messages.success(request, f"Country '{name}' added successfully.")
        
        elif action == "add_city":
            name = request.POST.get('name')
            country_id = request.POST.get('country_id')
            country = get_object_or_404(Country, id=country_id)
            City.objects.create(name=name, country=country)
            messages.success(request, f"City '{name}' added to {country.name}.")
            
        return redirect('manage_locations')
        
    return render(request, "manage_locations.html", {"countries": countries})

# DELETE COUNTRY
@login_required
@staff_member_required
def delete_country(request, id):
    country = get_object_or_404(Country, id=id)
    name = country.name
    country.delete()
    messages.warning(request, f"Country '{name}' and all its cities deleted.")
    return redirect('manage_locations')

# DELETE CITY
@login_required
@staff_member_required
def delete_city(request, id):
    city = get_object_or_404(City, id=id)
    name = city.name
    city.delete()
    messages.warning(request, f"City '{name}' deleted.")
    return redirect('manage_locations')

# MANAGE USERS (Admin Only)
@login_required
@staff_member_required
def manage_users(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    query = request.GET.get('search', '')
    role_filter = request.GET.get('role', 'All')
    
    users = RegisterModel.objects.all().order_by('-created_at')
    
    if query:
        users = users.filter(Q(full_name__icontains=query) | Q(username__icontains=query) | Q(email__icontains=query))
        
    if role_filter != 'All':
        users = users.filter(role=role_filter)
        
    # Also include Admins who might not have a 'register' profile for completeness if needed?
    # But usually all dashboard users are in the 'register' model in this app.
    
    return render(request, 'manage_users.html', {
        'users': users,
        'search': query,
        'role_filter': role_filter
    })

# DELETE USER
@login_required
@staff_member_required
def delete_user(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    reg = get_object_or_404(RegisterModel, id=id)
    user = reg.user
    name = reg.full_name
    
    # Don't let admin delete themselves
    if user == request.user:
        messages.error(request, "You cannot delete your own admin account.")
        return redirect('manage_users')
        
    user.delete() # Also deletes reg via cascade
    messages.warning(request, f"User '{name}' and their account have been removed.")
    
    referer = request.META.get('HTTP_REFERER')
    if referer and 'delete' not in referer:
        return redirect(referer)
    return redirect('manage_users')

# ADMIN REPORTS
@login_required
@staff_member_required
def admin_reports(request):
    if not request.user.is_superuser:
        return redirect('dashboard_redirect')

    # 1. Exhibition Stats
    total_exhibitions = Exhibition.objects.count()
    pending_exhibitions = Exhibition.objects.filter(status='pending').count()
    approved_exhibitions = Exhibition.objects.filter(status='approved').count()
    
    # 2. User Stats & Demographics
    total_users = RegisterModel.objects.count()
    visitors = RegisterModel.objects.filter(role='Visitor').count()
    organizers = RegisterModel.objects.filter(role='Organizer').count()
    
    # 3. Booking & Revenue Highlights
    total_bookings = Booking.objects.count()
    ticket_bookings = Booking.objects.filter(booking_type='ticket').count()
    stall_bookings = Booking.objects.filter(booking_type='stall').count()
    
    revenue_data = Booking.objects.aggregate(total=Sum('total_price'))
    total_revenue = revenue_data['total'] or 0
    
    # 4. Monthly Revenue Trend (Jan to Dec of Current Year)
    current_year = timezone.now().year
    rev_labels = [calendar.month_name[i][:3] for i in range(1, 13)] # ['Jan', 'Feb', ..., 'Dec']
    rev_values = []
    
    for i in range(1, 13):
        # Calculate monthly totals for the current year
        month_rev = Booking.objects.filter(
            created_at__year=current_year,
            created_at__month=i,
            payment_status='completed'
        ).aggregate(total=Sum('total_price'))['total'] or 0
        rev_values.append(float(month_rev))
    
    # 4.5 Extra KPIs for SaaS Layout
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_organizers = RegisterModel.objects.filter(role='Organizer', created_at__gte=thirty_days_ago).count()
    
    total_system_stalls = Exhibition.objects.aggregate(t=Sum('total_stalls'))['t'] or 0
    occupied_stalls = Booking.objects.filter(booking_type='stall', payment_status='completed').count()
    reserved_stalls = Booking.objects.filter(booking_type='stall', payment_status='pending').count()
    available_stalls = max(0, total_system_stalls - occupied_stalls - reserved_stalls)

    # 5. Top 5 Exhibitions by Revenue
    top_exhibitions = Exhibition.objects.annotate(
        total_rev=Sum('booking__total_price', filter=Q(booking__payment_status='completed')),
        registrations_count=Count('booking')
    ).order_by('-total_rev')[:5]

    # 6. Category Distribution
    categories = Category.objects.annotate(count=Count('exhibition')).order_by('-count')[:5]
    total_cat_count = sum(c.count for c in categories) if categories else 1
    
    # 7. Recent Transactions (Kept for compatibility if needed, though not in the image)
    recent_bookings = Booking.objects.all().select_related('user', 'exhibition').order_by('-created_at')[:10]
    
    # AJAX Polling Support
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'stats': {
                'total_revenue': float(total_revenue),
                'total_users': total_users,
                'approved_exhibitions': approved_exhibitions,
                'new_organizers': new_organizers,
                'occupied_stalls': occupied_stalls,
                'reserved_stalls': reserved_stalls,
                'available_stalls': available_stalls,
                'occupancy_pct': round((occupied_stalls / total_system_stalls * 100)) if total_system_stalls > 0 else 0
            },
            'charts': {
                'revenue': {'labels': rev_labels, 'values': rev_values}
            }
        })
    
    return render(request, 'reports.html', {
        'today': timezone.now(),
        'total_exhibitions': total_exhibitions,
        'approved_exhibitions': approved_exhibitions,
        'total_users': total_users,
        'new_organizers': new_organizers,
        'total_revenue': total_revenue,
        'rev_labels': rev_labels,
        'rev_values': rev_values,
        'top_exhibitions': top_exhibitions,
        'categories': categories,
        'total_cat_count': total_cat_count,
        'occupied_stalls': occupied_stalls,
        'reserved_stalls': reserved_stalls,
        'available_stalls': available_stalls,
        'total_system_stalls': total_system_stalls or 1,
    })

@login_required
def manage_stalls(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)
    
    # Permission check
    if not request.user.is_superuser and exhibition.user != request.user:
        messages.error(request, "You do not have permission to manage stalls for this exhibition.")
        return redirect('list_exhibition')

    # 1. Sync stalls based on exhibition capacity (similar to public view)
    current_stalls = list(exhibition.stalls_list.all().order_by('id'))
    expected_count = exhibition.total_stalls or 20
    base_price = exhibition.stall_price or Decimal('500.00')

    # Add stalls if needed
    if len(current_stalls) < expected_count:
        existing_nums = {s.stall_number for s in current_stalls}
        stalls_to_create = []
        needed = expected_count - len(current_stalls)
        created = 0
        i = 1
        while created < needed:
            row_idx = (i - 1) // 6 
            num_in_row = (i - 1) % 6 + 1
            row_letter = chr(65 + row_idx) 
            stall_num = f"{row_letter}{num_in_row:02d}"
            
            if stall_num not in existing_nums:
                is_large = (row_letter == 'A')
                stalls_to_create.append(Stall(
                    exhibition=exhibition,
                    stall_number=stall_num,
                    stall_type='large' if is_large else 'small',
                    price=base_price * Decimal('1.5') if is_large else base_price,
                    dimensions='3m x 6m (18sqm)' if is_large else '3m x 3m (9sqm)',
                    position='Premium Row' if is_large else 'Standard Aisle',
                ))
                existing_nums.add(stall_num)
                created += 1
            i += 1
        if stalls_to_create:
            Stall.objects.bulk_create(stalls_to_create)

    is_complete = exhibition.dynamic_status == 'Complete'

    # 2. Handle AJAX/POST updates
    if request.method == "POST":
        if is_complete:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'This exhibition is complete and cannot be edited.'}, status=403)
            messages.error(request, "This exhibition is complete and cannot be edited.")
            return redirect('manage_stalls', id=id)

        action = request.POST.get('action')
        stall_id = request.POST.get('stall_id')
        stall = get_object_or_404(Stall, id=stall_id, exhibition=exhibition)

        if action == "update_stall":
            stall.price = Decimal(request.POST.get('price', stall.price))
            stall.dimensions = request.POST.get('dimensions', stall.dimensions)
            stall.position = request.POST.get('position', stall.position)
            stall.stall_type = request.POST.get('stall_type', stall.stall_type)
            # Update status if provided
            new_status = request.POST.get('status')
            if new_status in dict(Stall.STALL_STATUS):
                stall.status = new_status
            stall.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': f'Stall {stall.stall_number} updated.'})
            messages.success(request, f"Stall {stall.stall_number} updated.")

        elif action == "update_global_pricing":
            new_base_price = Decimal(request.POST.get('base_price', exhibition.stall_price))
            apply_to_all = request.POST.get('apply_to_all') == 'true'
            
            exhibition.stall_price = new_base_price
            exhibition.save()
            
            if apply_to_all:
                exhibition.stalls_list.update(price=new_base_price)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Global pricing updated successfully.',
                    'new_price': str(new_base_price)
                })
            messages.success(request, "Global pricing updated.")

        elif action == "toggle_status":
            # Direct toggle for quick actions if needed, or specific status set
            current_status = stall.status
            if current_status == 'available':
                stall.status = 'booked'
            elif current_status == 'booked':
                stall.status = 'maintenance'
            else:
                stall.status = 'available'
            stall.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'new_status': stall.status,
                    'message': f'Stall {stall.stall_number} status updated to {stall.status}.'
                })
            messages.success(request, f"Stall {stall.stall_number} status updated.")
        
        return redirect('manage_stalls', id=id)

    stalls = exhibition.stalls_list.all().order_by('stall_number')
    booked_stalls = exhibition.stalls_list.filter(status='booked').count()
    available_stalls = exhibition.stalls_list.filter(status='available').count()
    maintenance_stalls = exhibition.stalls_list.filter(status='maintenance').count()

    # Get booking info for each booked stall
    stall_bookings_data = {}
    bookings = Booking.objects.filter(exhibition=exhibition, booking_type='stall', stall_instance__isnull=False)
    for b in bookings:
        stall_bookings_data[b.stall_instance_id] = {
            'user': b.user.username,
            'full_name': b.user.first_name + " " + b.user.last_name,
            'email': b.user.email,
            'date': b.created_at.strftime('%Y-%m-%d %H:%M'),
            'price': float(b.total_price)
        }

    context = {
        'exhibition': exhibition,
        'stalls': stalls,
        'available_stalls': available_stalls,
        'booked_stalls': booked_stalls,
        'maintenance_stalls': maintenance_stalls,
        'stall_bookings': stall_bookings_data,
        'role': 'Organizer',
        'is_complete': is_complete,
    }
    return render(request, 'manage_stalls.html', context)

@login_required
def profile_settings(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == "POST":
        if 'full_name' in request.POST:
            profile.full_name = request.POST.get('full_name')
        if 'mobile' in request.POST:
            profile.mobile = request.POST.get('mobile')
        if 'address' in request.POST:
            profile.address = request.POST.get('address')
        if 'email' in request.POST:
            new_email = request.POST.get('email')
            if new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                    messages.error(request, "This email is already in use by another user.")
                    return redirect('profile_settings')
                
                request.user.email = new_email
                request.user.save()
                # Sync with RegisterModel
                RegisterModel.objects.filter(user=request.user).update(email=new_email)

        if 'gov_id_type' in request.POST:
            profile.gov_id_type = request.POST.get('gov_id_type')
        if 'gov_id_number' in request.POST:
            profile.gov_id_number = request.POST.get('gov_id_number')
        
        if request.FILES.get('gov_id_upload'):
            profile.gov_id_upload = request.FILES.get('gov_id_upload')
            
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES.get('avatar')
            
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('profile_settings')
        
    return render(request, 'profile.html', {'profile': profile})

# NOTIFICATIONS VIEWS

@login_required
def list_notifications(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'list_notifications.html', {'notifications': notifications})

@login_required
def notification_detail(request, id):
    notification = get_object_or_404(Notification, id=id, user=request.user)
    notification.is_read = True
    notification.save()
    return render(request, 'notification_detail.html', {'notification': notification})

# NOTIFICATIONS API

@login_required
def fetch_notifications(request):
    notifications = request.user.notifications.all()[:5]
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'is_read': notif.is_read,
            'link': notif.link,
            'type': notif.notification_type,
            'created_at': notif.created_at.strftime('%b %d, %Y %H:%M'),
        })
        
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': data
    })

@login_required
def mark_notification_read(request, id):
    notif = get_object_or_404(Notification, id=id, user=request.user)
    notif.is_read = True
    notif.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    if notif.link:
        return redirect(notif.link)
    return redirect('dashboard_redirect')

@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('dashboard_redirect')
