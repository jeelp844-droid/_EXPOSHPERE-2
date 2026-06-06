import os
import django
import sys
from io import BytesIO

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'expo')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expo.settings')
django.setup()

from public.models import Booking
from public.utils import generate_booking_pdf
from public.email_utils import send_booking_email

def test_pdf_generation():
    print("Testing PDF Generation...")
    booking = Booking.objects.first()
    if not booking:
        print("No booking found in database to test with.")
        return
    
    pdf_buffer = generate_booking_pdf(booking)
    if pdf_buffer and len(pdf_buffer.getvalue()) > 0:
        print(f"Successfully generated PDF for booking {booking.id}. Size: {len(pdf_buffer.getvalue())} bytes")
        # Save to a temporary file for manual inspection if needed
        with open('test_pass.pdf', 'wb') as f:
            f.write(pdf_buffer.getvalue())
        print("PDF saved to test_pass.pdf")
    else:
        print("Failed to generate PDF.")

def test_email_sending():
    print("\nTesting Email Sending...")
    booking = Booking.objects.first()
    if not booking:
        print("No booking found in database to test with.")
        return
    
    # NOTE: This will only work if SMTP settings are correctly configured in settings.py
    # and the recipient email is valid.
    print(f"Attempting to send confirmation email for booking {booking.id} to {booking.user.email}...")
    try:
        success = send_booking_email(booking, 'confirmed')
        if success:
            print("Email sent successfully (or at least queued without error).")
        else:
            print("Failed to send email. Check above for printed errors.")
    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check SITE_URL
    from django.conf import settings
    if not hasattr(settings, 'SITE_URL'):
        print("WARNING: SITE_URL is not defined in settings.py. Some links in emails might be broken.")
    
    try:
        test_pdf_generation()
        test_email_sending() 
    except Exception as e:
        import traceback
        traceback.print_exc()
