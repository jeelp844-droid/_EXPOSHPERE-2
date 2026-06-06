from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from .utils import generate_booking_pdf

def send_booking_email(booking, status):
    """
    Sends an email to the visitor regarding their booking status.
    If status is 'confirmed', attaches the generated PDF pass.
    """
    subject = f"Booking {status.title()}: {booking.exhibition.title}"
    
    context = {
        'booking': booking,
        'status': status,
        'ex_title': booking.exhibition.title,
        'user_name': booking.user.first_name or booking.user.username,
        'settings': settings,
    }
    
    if status == 'confirmed':
        template_name = 'email/booking_confirmed.html'
    elif status == 'cancelled':
        template_name = 'email/booking_cancelled.html'
    else:
        template_name = 'email/booking_status_update.html'
        
    try:
        print(f"--- PREPARING EMAIL: {subject} ---")
        print(f"Recipient: {booking.user.email}")
        print(f"Status: {status}")
        
        html_message = render_to_string(template_name, context)
        # Generate a plain-text version for better deliverability
        plain_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject,
            plain_message, # Use plain text as body
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            headers={'Auto-Submitted': 'auto-generated'}
        )
        email.attach_alternative(html_message, "text/html") # Attach HTML as alternative
        
        if status == 'confirmed':
            # Generate PDF and attach
            pdf_buffer = generate_booking_pdf(booking)
            filename = f"ExpoSphere_{booking.booking_type.capitalize()}_Pass_{booking.id}.pdf"
            email.attach(filename, pdf_buffer.getvalue(), 'application/pdf')
            
        print(f"Sending email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        email.send()
        print(f"--- EMAIL SENT SUCCESSFULLY ---")
        return True
    except Exception as e:
        import traceback
        print(f"--- ERROR SENDING EMAIL ---")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def send_organizer_approval_email(user_reg, status):
    """
    Sends an email to the user regarding their organizer registration status.
    """
    subject = f"Organizer Account {status.title()}"
    user = user_reg.user
    context = {
        'user_name': user_reg.full_name or user.username,
        'settings': settings,
    }
    
    template_name = f'email/organizer_{status}.html'
    try:
        print(f"--- PREPARING EMAIL: {subject} ---")
        print(f"Recipient: {user.email}")
        
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, 
            plain_message, 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            headers={'Auto-Submitted': 'auto-generated'}
        )
        email.attach_alternative(html_message, "text/html")
        
        print(f"Sending email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        email.send()
        print(f"--- EMAIL SENT SUCCESSFULLY ---")
        return True
    except Exception as e:
        import traceback
        print(f"--- ERROR SENDING EMAIL ---")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def send_exhibition_approval_email(exhibition, status):
    """
    Sends an email to the organizer regarding their exhibition approval status.
    """
    subject = f"Exhibition {status.title()}: {exhibition.title}"
    user = exhibition.user
    context = {
        'user_name': user.first_name or user.username,
        'ex_title': exhibition.title,
        'settings': settings,
    }
    
    template_name = f'email/exhibition_{status}.html'
    try:
        print(f"--- PREPARING EMAIL: {subject} ---")
        print(f"Recipient: {user.email}")
        
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, 
            plain_message, 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            headers={'Auto-Submitted': 'auto-generated'}
        )
        email.attach_alternative(html_message, "text/html")
        
        print(f"Sending email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        email.send()
        print(f"--- EMAIL SENT SUCCESSFULLY ---")
        return True
    except Exception as e:
        import traceback
        print(f"--- ERROR SENDING EMAIL ---")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def send_registration_email(user):
    """
    Sends a welcome email to the user after successful registration.
    """
    subject = f"Welcome to ExpoSphere, {user.first_name or user.username}!"
    context = {
        'user_name': user.first_name or user.username,
        'settings': settings,
    }
    
    template_name = 'email/registration_success.html'
    try:
        print(f"--- PREPARING WELCOME EMAIL: {subject} ---")
        print(f"Recipient: {user.email}")
        
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, 
            plain_message, 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            headers={'Auto-Submitted': 'auto-generated'}
        )
        email.attach_alternative(html_message, "text/html")
        
        print(f"Sending email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        email.send()
        print(f"--- WELCOME EMAIL SENT SUCCESSFULLY ---")
        return True
    except Exception as e:
        import traceback
        print(f"--- ERROR SENDING WELCOME EMAIL ---")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def send_login_email(user):
    """
    Sends a security alert email when a user logs in successfully.
    """
    subject = f"New Login to Your ExpoSphere Account"
    context = {
        'user_name': user.first_name or user.username,
        'login_time': timezone.now().strftime('%b %d, %Y at %H:%M:%S'),
        'settings': settings,
    }
    
    template_name = 'email/login_success.html'
    try:
        print(f"--- PREPARING LOGIN SECURITY EMAIL: {subject} ---")
        print(f"Recipient: {user.email}")
        
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, 
            plain_message, 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            headers={'Auto-Submitted': 'auto-generated'}
        )
        email.attach_alternative(html_message, "text/html")
        
        print(f"Sending email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        email.send()
        print(f"--- LOGIN SECURITY EMAIL SENT SUCCESSFULLY ---")
        return True
    except Exception as e:
        import traceback
        print(f"--- ERROR SENDING LOGIN SECURITY EMAIL ---")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
