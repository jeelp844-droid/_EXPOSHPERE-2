from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q, Case, When, Value, IntegerField, F, ExpressionWrapper
from django.db.models.functions import Coalesce
from public.models import Category, City, Contact, Country, Exhibition, Booking, Stall, Notification, Enquiry, register as RegisterModel
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import qrcode
import random
import string
from .email_utils import send_registration_email, send_login_email

# Create your views here.

# INDEX PAGE 
def index(request):
    # Dynamic Stats
    country_count = Country.objects.count()
    exhibition_count = Exhibition.objects.filter(status='approved').count()
    # Using total bookings as a proxy for visitors, or a large starting number + actual bookings
    visitor_count = Booking.objects.count() + 1000000 
    organizer_count = RegisterModel.objects.filter(role='Organizer').count() + 10000

    # Upcoming Exhibitions (Top 3)
    now = timezone.now()
    upcoming_exhibitions = Exhibition.objects.filter(
        status='approved',
        end_date__gte=now.date()
    ).order_by('start_date')[:3]

    context = {
        "country_count": country_count,
        "exhibition_count": exhibition_count,
        "visitor_count": visitor_count,
        "organizer_count": organizer_count,
        "upcoming_exhibitions": upcoming_exhibitions,
    }
    return render(request, 'index.html', context)

# ABOUT PAGE 
def about(request):
    return render(request, 'about.html')

# Contact PAGE 
def contact(request):
    if request.method=='POST':
        fname=request.POST.get('fname')
        lname=request.POST.get('lname')
        email=request.POST.get('email')
        subject=request.POST.get('subject')
        message=request.POST.get('message')
        Contact.objects.create(fname=fname, lname=lname, email=email, subject=subject, message=message)
        messages.success(request, "Your message has been sent successfully!")
        return redirect('contact')
    return render(request, 'contact.html')

# How It Work
def Work(request):
    return render(request, 'HowItWork.html')

# Register
def register(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('/register/')

        # Username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists")
            return redirect('/register/')

        # Email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' already registered")
            return redirect('/register/')

        # Mobile exists
        from public.models import register as RegisterModel
        if RegisterModel.objects.filter(mobile=mobile).exists():
            messages.error(request, f"Contact number '{mobile}' already registered")
            return redirect('/register/')

        # Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name
        )
        user.save()

        # Create Register record (Profile)
        from public.models import register as RegisterModel
        role = request.POST.get('role', 'Visitor')
        RegisterModel.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            mobile=mobile,
            username=username,
            password=password,
            role=role,
            is_approved=(role == 'Visitor') # Visitors auto-approved, Organizers need admin
        )

        # Notify Superusers if Organizer registers
        if role == 'Organizer':
            superusers = User.objects.filter(is_superuser=True)
            for admin in superusers:
                Notification.objects.create(
                    user=admin,
                    title="New Organizer Registered",
                    message=f"A new organizer '{full_name}' has registered and awaits approval.",
                    notification_type='admin',
                    link="/dashboard/list_organizers/"
                )
        
        # Send Welcome Email
        send_registration_email(user)

        messages.success(request, "Registration Successful. Please Login.")
        return redirect('/login/')

    return render(request, 'register.html')

# Login
def delogin(request):
    if request.method == "POST":
        username = request.POST.get("username")   # FIXED
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(1209600) # 2 weeks
            else:
                request.session.set_expiry(0) # on browser close
            
            # Send Login Security Email
            send_login_email(user)

            messages.success(request, "Login Successful")
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('/login/')

    return render(request, 'login.html')

# Logout
def user_logout(request):
    logout(request)
    return redirect('/login/')

# Exhibition Page
def exhibition(request):
    exhibitions = Exhibition.objects.filter(status='approved').order_by('-id')

    countries = Country.objects.all()
    cities = City.objects.all()

    search = request.GET.get('search')
    category = request.GET.get('category')
    country = request.GET.get('country')
    city = request.GET.get('city')
    status = request.GET.get('status')

    if search:
        exhibitions = exhibitions.filter(title__icontains=search)

    if category and category != "All":
        if category.isdigit():
            exhibitions = exhibitions.filter(category_id=category)
        else:
            exhibitions = exhibitions.filter(category__name=category)

    if country:
        exhibitions = exhibitions.filter(country_id=country)
        cities = City.objects.filter(country_id=country)

    if city:
        exhibitions = exhibitions.filter(city_id=city)

    # Temporal status filtering (Month-based with end_date check)
    now = timezone.now()
    today = now.date()
    current_year = now.year
    current_month = now.month

    if status == "Upcoming":
        exhibitions = exhibitions.filter(
            Q(start_date__year__gt=current_year) | 
            Q(start_date__year=current_year, start_date__month__gt=current_month)
        ).filter(end_date__gte=today)
    elif status == "Ongoing":
        exhibitions = exhibitions.filter(
            start_date__year=current_year, 
            start_date__month=current_month,
            end_date__gte=today
        )
    elif status == "Complete":
        exhibitions = exhibitions.filter(
            Q(end_date__lt=today) |
            Q(start_date__year__lt=current_year) | 
            Q(start_date__year=current_year, start_date__month__lt=current_month)
        )

    # Arranged format: Sort by status (Ongoing > Upcoming > Complete)
    exhibitions = exhibitions.annotate(
        sort_order=Case(
            # Ongoing: Present month AND not ended
            When(start_date__year=current_year, start_date__month=current_month, end_date__gte=today, then=Value(1)),
            # Upcoming: Future month AND not ended
            When(Q(start_date__year__gt=current_year) | Q(start_date__year=current_year, start_date__month__gt=current_month), end_date__gte=today, then=Value(2)),
            # Complete: Everything else
            default=Value(3),
            output_field=IntegerField(),
        )
    ).annotate(
        booked=Coalesce(Sum('booking__standard_qty', filter=Q(booking__status='confirmed')), 0) +
               Coalesce(Sum('booking__student_qty', filter=Q(booking__status='confirmed')), 0) +
               Coalesce(Sum('booking__vip_qty', filter=Q(booking__status='confirmed')), 0)
    ).annotate(
        available_tickets=ExpressionWrapper(F('total_tickets') - F('booked'), output_field=IntegerField())
    ).order_by('sort_order', 'start_date')
    # If status is something else (like from model choices), we skip it or handle it separately.
    # But usually, it's 'approved' which is already filtered at the top.

    context = {
        "exhibitions": exhibitions,
        "countries": countries,
        "cities": cities,
        "categories": Category.objects.all(),
    }

    return render(request,'exhibition.html',context)

# AJAX CITY LOAD
def load_cities(request):

    country_id = request.GET.get('country')

    cities = City.objects.filter(country_id=country_id).values('id','name')

    return JsonResponse(list(cities), safe=False)

def exhibition_detail(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)
    
    # Calculate live stall availability
    booked_stalls = Booking.objects.filter(exhibition=exhibition, booking_type='stall').aggregate(Sum('stalls'))['stalls__sum'] or 0
    available_stalls = max(0, exhibition.total_stalls - booked_stalls)

    # Calculate live ticket availability
    booked_tickets_data = Booking.objects.filter(exhibition=exhibition, booking_type='ticket', status='confirmed').aggregate(
        std=Sum('standard_qty'),
        stu=Sum('student_qty'),
        vip=Sum('vip_qty')
    )
    booked_tickets = (booked_tickets_data['std'] or 0) + (booked_tickets_data['stu'] or 0) + (booked_tickets_data['vip'] or 0)
    available_tickets = max(0, exhibition.total_tickets - booked_tickets)

    # Fetch user role from register model if authenticated
    user_role = None
    if request.user.is_authenticated:
        reg_record = RegisterModel.objects.filter(user=request.user).first()
        if reg_record:
            user_role = reg_record.role
            
    # Fetch Enquiries
    enquiries = Enquiry.objects.filter(exhibition=exhibition).select_related('user').order_by('-created_at')

    context = {
        'exhibition': exhibition,
        'available_stalls': available_stalls,
        'booked_stalls': booked_stalls,
        'available_tickets': available_tickets,
        'booked_tickets': booked_tickets,
        'role': user_role,
        'enquiries': enquiries,
    }
    return render(request, 'exhibition_detail.html', context)

def book_tickets(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)

    if exhibition.dynamic_status == 'Complete':
        messages.error(request, "This exhibition has already concluded. Booking is closed.")
        return redirect('exhibition_detail', id=id)
    if request.user.is_superuser:
        messages.error(request, "Admins cannot book tickets.")
        return redirect('exhibition_detail', id=id)
    if exhibition.user == request.user:
        messages.error(request, "Organizers cannot book tickets or stalls for their own exhibitions.")
        return redirect('exhibition_detail', id=id)
    
    # Base price from model is Standard price
    standard_price = exhibition.ticket_price
    student_price = standard_price * Decimal('0.5')
    vip_price = standard_price * Decimal('2.0')

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please login to book tickets.")
            return redirect('delogin')

        student_qty = int(request.POST.get('student_qty', 0))
        standard_qty = int(request.POST.get('standard_qty', 0))
        vip_qty = int(request.POST.get('vip_qty', 0))
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        
        total_requested = student_qty + standard_qty + vip_qty
        
        if total_requested <= 0:
            messages.error(request, "Please select at least one ticket.")
            return redirect('book_tickets', id=id)

        # Check availability
        booked_tickets_data = Booking.objects.filter(exhibition=exhibition, booking_type='ticket', status='confirmed').aggregate(
            std=Sum('standard_qty'),
            stu=Sum('student_qty'),
            vip=Sum('vip_qty')
        )
        booked_tickets = (booked_tickets_data['std'] or 0) + (booked_tickets_data['stu'] or 0) + (booked_tickets_data['vip'] or 0)
        available_tickets = exhibition.total_tickets - booked_tickets

        if total_requested > available_tickets:
            messages.error(request, f"Sorry, only {available_tickets} tickets are available.")
            return redirect('book_tickets', id=id)
            
        # Initial Total Calculation
        total_price = (student_qty * student_price) + (standard_qty * standard_price) + (vip_qty * vip_price)
        
        student_id_proof = request.FILES.get('student_id_proof')
        
        # Create Booking
        booking = Booking.objects.create(
            user=request.user,
            exhibition=exhibition,
            stalls=total_requested, 
            booking_type='ticket',
            student_qty=student_qty,
            standard_qty=standard_qty,
            vip_qty=vip_qty,
            total_price=total_price,
            razorpay_payment_id=razorpay_payment_id,
            payment_status='completed' if razorpay_payment_id else 'pending',
            student_id_proof=student_id_proof,
            status='confirmed'
        )
        
        # Send Confirmation Email
        from .email_utils import send_booking_email
        send_booking_email(booking, 'confirmed')
        
        # Create Notifications
        # 1. Notify Visitor
        Notification.objects.create(
            user=request.user,
            title="Ticket Booking Confirmed",
            message=f"Your booking for {total_requested} ticket(s) to '{exhibition.title}' is confirmed.",
            notification_type='visitor',
            link="/dashboard/my-bookings/"
        )
        
        # 2. Notify Organizer
        Notification.objects.create(
            user=exhibition.user,
            title="New Ticket Booking",
            message=f"'{request.user.username}' just booked {total_requested} ticket(s) for your exhibition '{exhibition.title}'.",
            notification_type='organizer',
            link="/dashboard/my-exhibition-book/"
        )

        messages.success(request, f"Successfully booked {total_requested} ticket(s) for ₹{total_price:,.2f}!")
        return redirect('booking_success', booking_id=booking.id)

    # Calculate live ticket availability for display
    booked_tickets_data = Booking.objects.filter(exhibition=exhibition, booking_type='ticket', status='confirmed').aggregate(
        std=Sum('standard_qty'),
        stu=Sum('student_qty'),
        vip=Sum('vip_qty')
    )
    booked_tickets = (booked_tickets_data['std'] or 0) + (booked_tickets_data['stu'] or 0) + (booked_tickets_data['vip'] or 0)
    available_tickets = max(0, exhibition.total_tickets - booked_tickets)

    context = {
        'exhibition': exhibition,
        'student_price': student_price,
        'standard_price': standard_price,
        'vip_price': vip_price,
        'available_tickets': available_tickets,
    }
    return render(request, 'book_tickets.html', context)

def book_stall(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)

    if exhibition.dynamic_status == 'Complete':
        messages.error(request, "This exhibition has already concluded. Stall booking is closed.")
        return redirect('exhibition_detail', id=id)

    if request.user.is_superuser:
        messages.error(request, "Admins cannot book stalls.")
        return redirect('exhibition_detail', id=id)

    if exhibition.user == request.user:
        messages.error(request, "Organizers cannot book tickets or stalls for their own exhibitions.")
        return redirect('exhibition_detail', id=id)

    current_stalls = list(exhibition.stalls_list.all().order_by('id'))
    expected_count = exhibition.total_stalls or 20
    base_price = exhibition.stall_price or Decimal('500.00')

    # 1. Update prices of existing unbooked stalls to match current exhibition base price
    for stall in current_stalls:
        if stall.status != 'booked':
            is_large = stall.stall_number.startswith('A')
            new_price = base_price * Decimal('1.5') if is_large else base_price
            if stall.price != new_price:
                stall.price = new_price
                stall.save()

    # 2. Add stalls if exhibition capacity increased
    if len(current_stalls) < expected_count:
        existing_nums = {s.stall_number for s in current_stalls}
        stalls_to_create = []
        needed = expected_count - len(current_stalls)
        created = 0
        i = 1

        while created < needed:
            stall_num = f"{i:02d}"
            if stall_num not in existing_nums:
                is_large = stall_num.startswith('0') or i > 15
                stalls_to_create.append(Stall(
                    exhibition=exhibition,
                    stall_number=stall_num,
                    stall_type='large' if is_large else 'small',
                    price=base_price * Decimal('1.5') if is_large else base_price,
                    dimensions='3m x 6m (18sqm)' if is_large else '3m x 3m (9sqm)',
                    position='Premium Row' if is_large else 'Standard Aisle',
                    amenities='High-speed WiFi (100Mbps), Dual 220V Power Outlets, 2 Chairs & 1 Information Desk, 3 Spotlight Fixtures'
                ))
                existing_nums.add(stall_num)
                created += 1
            i += 1

        if stalls_to_create:
            Stall.objects.bulk_create(stalls_to_create)

    # 3. Remove excess stalks if exhibition capacity decreased (only unbooked ones)
    elif len(current_stalls) > expected_count:
        excess = len(current_stalls) - expected_count
        for stall in reversed(current_stalls):
            if stall.status != 'booked' and excess > 0:
                stall.delete()
                excess -= 1

    stalls = exhibition.stalls_list.all().order_by('stall_number')
    booked_stalls = exhibition.stalls_list.filter(status='booked').count()
    available_stalls = max(0, exhibition.total_stalls - booked_stalls)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please login to book a stall.")
            return redirect('delogin')

        # Role Check: Only Organizers can book stalls
        reg_record = RegisterModel.objects.filter(user=request.user).first()
        if reg_record and reg_record.role != 'Organizer':
            messages.error(request, "Only Organizers can book stalls. Visitors should book tickets.")
            return redirect('exhibition_detail', id=id)

        stall_id = request.POST.get('stall_id')
        if not stall_id:
            messages.error(request, "Please select a stall from the floor plan.")
            return redirect('book_stall', id=id)

        stall = get_object_or_404(Stall, id=stall_id, exhibition=exhibition)

        if stall.status == 'booked':
            messages.error(request, "This stall has already been reserved.")
            return redirect('book_stall', id=id)

        return redirect('stall_details', stall_id=stall_id)

    context = {
        'exhibition': exhibition,
        'stalls': stalls,
        'available_stalls': available_stalls,
    }
    return render(request, 'book_stall.html', context)

@login_required
def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.user != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('index')

    return render(request, 'booking_success.html', {'booking': booking})

def send_enquiry(request, id):
    exhibition = get_object_or_404(Exhibition, id=id)

    if exhibition.dynamic_status == 'Complete':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Inquiries are closed as this exhibition has already concluded.'})
        messages.error(request, "Inquiries are closed as this exhibition has already concluded.")
        return redirect('exhibition_detail', id=id)

    if request.user.is_superuser:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Admins cannot send enquiries.'})
        messages.error(request, "Admins cannot send enquiries.")
        return redirect('exhibition_detail', id=id)

    if exhibition.user == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Organizers cannot send inquiries for their own exhibitions.'})
        messages.error(request, "Organizers cannot send inquiries for their own exhibitions.")
        return redirect('exhibition_detail', id=id)

    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Please login to send an enquiry.'})
        messages.error(request, "Please login to send an enquiry.")
        return redirect('delogin')
    
    if request.method == "POST":
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        if not subject or not message:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Subject and message are required.'})
            messages.error(request, "Subject and message are required.")
            return redirect('exhibition_detail', id=id)

        from public.models import Enquiry
        enquiry = Enquiry.objects.create(
            user=request.user,
            exhibition=exhibition,
            subject=subject,
            message=message
        )
        
        # Create Notifications
        Notification.objects.create(
            user=request.user,
            title="Enquiry Sent",
            message=f"Your enquiry about '{exhibition.title}' has been sent to the organizer.",
            notification_type='visitor',
            link="/dashboard/enquiries/"
        )
        
        Notification.objects.create(
            user=exhibition.user,
            title="New Enquiry Received",
            message=f"You have a new enquiry from '{request.user.username}' regarding '{exhibition.title}'.",
            notification_type='organizer',
            link="/dashboard/my-enquiries/"
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': 'Your enquiry has been sent successfully!',
                'enquiry': {
                    'subject': enquiry.subject,
                    'message': enquiry.message,
                    'created_at': enquiry.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'user': enquiry.user.username
                }
            })

        messages.success(request, "Your enquiry has been sent to the organizer successfully!")
        return redirect('exhibition_detail', id=id)
        
    return redirect('exhibition_detail', id=id)

    

# Forgot Password
def forgot_password(request):
    if request.method == "POST":
        query = request.POST.get("email_or_username")
        user = User.objects.filter(Q(email=query) | Q(username=query)).first()
        
        if user:
            return redirect('reset_password', id=user.id)
        else:
            messages.error(request, "User not found with this email or username.")
            return redirect('forgot_password')
            
    return render(request, 'forgot_password.html')

# Reset Password
def reset_password(request, id):
    user = get_object_or_404(User, id=id)
    
    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password', id=id)
            
        user.set_password(password)
        user.save()
        
        # Also update custom register model if it exists
        from public.models import register as RegisterModel
        reg_record = RegisterModel.objects.filter(user=user).first()
        if reg_record:
            reg_record.password = password
            reg_record.save()
            
        messages.success(request, "Password reset successful. Please login.")
        return redirect('delogin')
        
    return render(request, 'reset_password.html', {'user': user})

@login_required
def download_pass(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permission
    if not request.user.is_superuser and booking.user != request.user:
        messages.error(request, "Permission denied.")
        return redirect('dashboard_redirect')
        
    exhibition = booking.exhibition
    # Generate PDF using utility
    from .utils import generate_booking_pdf
    buffer = generate_booking_pdf(booking)
    
    return FileResponse(buffer, as_attachment=True, filename=f"ExpoSphere_{booking.booking_type.capitalize()}_Pass_{booking.id}.pdf")

@login_required
def stall_details(request, stall_id):
    stall = get_object_or_404(Stall, id=stall_id)
    exhibition = stall.exhibition
    
    if request.user.is_superuser:
        messages.error(request, "Admins cannot book stalls.")
        return redirect('exhibition_detail', id=exhibition.id)

    if exhibition.user == request.user:
        messages.error(request, "Organizers cannot book tickets or stalls for their own exhibitions.")
        return redirect('exhibition_detail', id=exhibition.id)

    if request.method == 'POST':
        # Capture details and equipment
        company_name = request.POST.get('company_name')
        representative_name = request.POST.get('representative_name')
        contact_number = request.POST.get('contact_number')
        stall_description = request.POST.get('stall_description')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        
        has_extra_chairs = request.POST.get('has_extra_chairs') == 'true'
        has_spotlight = request.POST.get('has_spotlight') == 'true'
        has_power_strip = request.POST.get('has_power_strip') == 'true'
        has_tv_display = request.POST.get('has_tv_display') == 'true'
        has_brochure_stand = request.POST.get('has_brochure_stand') == 'true'
        has_wifi = request.POST.get('has_wifi') == 'true'
        
        # Pricing Calculations
        base_price = Decimal(stall.price)
        addons_price = Decimal('0')
        
        if has_extra_chairs: addons_price += Decimal('15')
        if has_spotlight: addons_price += Decimal('45')
        if has_power_strip: addons_price += Decimal('10')
        if has_tv_display: addons_price += Decimal('120')
        if has_brochure_stand: addons_price += Decimal('25')
        if has_wifi: addons_price += Decimal('50')
        
        service_fee = Decimal('12.50')
        total_amount = base_price + addons_price + service_fee
        
        # Create Final Booking directly from details
        booking = Booking.objects.create(
            user=request.user,
            exhibition=exhibition,
            stalls=1,
            stall_instance=stall,
            booking_type='stall',
            total_price=total_amount,
            status='confirmed',
            payment_status='completed' if razorpay_payment_id else 'pending',
            razorpay_payment_id=razorpay_payment_id,
            company_name=company_name,
            representative_name=representative_name,
            contact_number=contact_number,
            stall_description=stall_description,
            has_extra_chairs=has_extra_chairs,
            has_spotlight=has_spotlight,
            has_power_strip=has_power_strip,
            has_tv_display=has_tv_display,
            has_brochure_stand=has_brochure_stand,
            has_wifi=has_wifi,
        )
        
        # Send Confirmation Email
        from .email_utils import send_booking_email
        send_booking_email(booking, 'confirmed')
        
        # Update Stall Status
        stall.status = 'booked'
        stall.save()
        
        # Create Notifications
        # 1. Notify Visitor
        Notification.objects.create(
            user=request.user,
            title="Stall Booking Confirmed",
            message=f"Success! Your stall #{stall.stall_number} for '{exhibition.title}' has been booked.",
            notification_type='visitor',
            link="/dashboard/my-bookings/"
        )
        
        # 2. Notify Organizer
        Notification.objects.create(
            user=exhibition.user,
            title="New Stall Reservation",
            message=f"'{request.user.username}' has reserved stall #{stall.stall_number} for your exhibition '{exhibition.title}'.",
            notification_type='organizer',
            link="/dashboard/my-exhibition-book/"
        )
        
        return redirect('booking_success', booking_id=booking.id)

    return render(request, 'stall_details.html', {
        'stall': stall,
        'exhibition': exhibition,
    })

def set_social_role(request):
    """
    Helper view to set the preferred role in session before initiating 
    social login.
    """
    role = request.GET.get('role', 'Visitor')
    if role in ['Visitor', 'Organizer']:
        request.session['social_role'] = role
    return JsonResponse({'status': 'ok'})


