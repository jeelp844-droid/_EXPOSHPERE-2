import io
import random
import string
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle

def generate_booking_pdf(booking):
    """
    Generates a PDF pass for a given booking.
    Returns a BytesIO buffer containing the PDF data.
    """
    exhibition = booking.exhibition
    
    # Generate Random Ticket Number (e.g. TK-492837)
    ticket_no = ''.join(random.choices(string.digits, k=6))
    full_ticket_id = f"TK-{ticket_no}"
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Background Aesthetic
    p.setFillColor(colors.HexColor("#F8FAFC")) # Light slate bg
    p.rect(0, 0, width, height, fill=1)
    
    # Draw Ticket Frame
    t_x, t_y = 0.5*inch, height - 6.5*inch
    t_w, t_h = 7.5*inch, 6.0*inch
    
    p.setStrokeColor(colors.HexColor("#E2E8F0"))
    p.setFillColor(colors.white)
    p.roundRect(t_x, t_y, t_w, t_h, 20, stroke=1, fill=1)
    
    # Accent Bar (Blue - Project Theme)
    p.setFillColor(colors.HexColor("#0B50DA")) 
    p.roundRect(t_x, t_y + t_h - 0.7*inch, t_w, 0.7*inch, 10, stroke=0, fill=1)
    
    # Header Text
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(t_x + 0.5*inch, t_y + t_h - 0.45*inch, "EXPOSPHERE ENTRY PASS")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(t_x + t_w - 0.5*inch, t_y + t_h - 0.4*inch, "OFFICIAL DIGITAL TICKET")

    # Content Area Top Y
    content_top_y = t_y + t_h - 0.9*inch
    
    # Content Columns
    p.setFillColor(colors.black)
    
    # LEFT COLUMN - Event Details
    col1_x = t_x + 0.5*inch
    cur_y = content_top_y - 0.2*inch
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(col1_x, cur_y, exhibition.title)
    cur_y -= 0.2*inch
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.gray)
    p.drawString(col1_x, cur_y, f"Category: {exhibition.category}")
    cur_y -= 0.4*inch
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(col1_x, cur_y, "DATE & TIME")
    cur_y -= 0.2*inch
    p.setFont("Helvetica", 10)
    p.drawString(col1_x, cur_y, f"{exhibition.start_date.strftime('%B %d, %Y')} • {exhibition.start_time.strftime('%I:%M %p') if exhibition.start_time else '09:00 AM'}")
    cur_y -= 0.4*inch
    
    # VENUE
    p.setFont("Helvetica-Bold", 10)
    p.drawString(col1_x, cur_y, "VENUE")
    cur_y -= 0.17*inch
    p.setFont("Helvetica", 9)
    p.drawString(col1_x, cur_y, exhibition.venue)
    cur_y -= 0.13*inch
    p.drawString(col1_x, cur_y, f"{exhibition.city.name}, {exhibition.country.name}")
    cur_y -= 0.4*inch
    
    # BOOKING SUMMARY
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(col1_x, cur_y, "BOOKING SUMMARY")
    cur_y -= 0.17*inch
    p.setFont("Helvetica", 9)
    p.drawString(col1_x, cur_y, f"Access Level: {booking.get_booking_type_display()}")
    cur_y -= 0.15*inch
    p.drawString(col1_x, cur_y, f"Total Quantity: {booking.stalls} Pass(es)")
    cur_y -= 0.25*inch
    
    if booking.booking_type == 'stall':
        equip_list = []
        if booking.has_extra_chairs: equip_list.append("Chairs")
        if booking.has_spotlight: equip_list.append("Spotlight")
        if booking.has_power_strip: equip_list.append("Power")
        if booking.has_tv_display: equip_list.append("TV")
        if booking.has_brochure_stand: equip_list.append("Stand")
        if booking.has_wifi: equip_list.append("WiFi")
        
        if equip_list:
            p.setFont("Helvetica", 8)
            p.drawString(col1_x, cur_y, "EQUIPMENT:")
            cur_y -= 0.15*inch
            p.setFont("Helvetica-Oblique", 7)
            p.setFillColor(colors.gray)
            p.drawString(col1_x, cur_y, ", ".join(equip_list))
            
    # RIGHT COLUMN - Image Corner, Booking Details & Barcode
    col2_x = t_x + 4.8*inch
    r_cur_y = content_top_y - 1.2*inch
    
    # Exhibition Corner Image removed
    r_cur_y -= 0.2*inch
    
    # DRAW BARCODE - Entry Pass
    try:
        from reportlab.graphics.barcode import code128
        barcode_id = f"EXP{booking.id:04d}"
        barcode = code128.Code128(barcode_id, barHeight=0.6*inch, barWidth=1.3)
        barcode.drawOn(p, col2_x, r_cur_y)
        
        # Label Barcode
        r_cur_y -= 0.2*inch
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(colors.HexColor("#059669")) # Green priority
        p.drawCentredString(col2_x + 1.0*inch, r_cur_y, "ENTRY PASS SCANNER")
    except Exception:
        pass
        
    r_cur_y -= 0.6*inch
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(col2_x, r_cur_y, "TICKET NUMBER")
    r_cur_y -= 0.17*inch
    p.setFont("Helvetica", 11)
    p.setFillColor(colors.HexColor("#0B50DA"))
    p.drawString(col2_x, r_cur_y, full_ticket_id)
    r_cur_y -= 0.3*inch
    
    if booking.booking_type == 'stall':
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(col2_x, r_cur_y, "STALL SPECIFICATIONS:")
        r_cur_y -= 0.15*inch
        
        p.setFont("Helvetica", 8)
        
        if booking.stall_instance:
            s_type = booking.stall_instance.get_stall_type_display()
            s_dim = booking.stall_instance.dimensions
            p.drawString(col2_x, r_cur_y, f"Type: {s_type} ({s_dim})")
            r_cur_y -= 0.12*inch
            p.drawString(col2_x, r_cur_y, f"Position: {booking.stall_instance.position}")
            r_cur_y -= 0.12*inch
            
        if booking.company_name:
            p.drawString(col2_x, r_cur_y, f"Company: {booking.company_name}")
            r_cur_y -= 0.12*inch
        if booking.representative_name:
            p.drawString(col2_x, r_cur_y, f"Rep: {booking.representative_name}")
            r_cur_y -= 0.12*inch
            
            p.setFillColor(colors.HexColor("#0B50DA"))
            p.setFont("Helvetica-Bold", 14)
            r_cur_y -= 0.3*inch
            p.drawString(col2_x, r_cur_y, f"STALL: #{booking.stall_instance.stall_number if booking.stall_instance else 'N/A'}")
    else:
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(col2_x, r_cur_y, "Ticket Breakdown:")
        r_cur_y -= 0.15*inch
        p.setFont("Helvetica", 9)
        
        if booking.student_qty > 0:
            p.drawString(col2_x, r_cur_y, f"- Student: {booking.student_qty}")
            r_cur_y -= 0.15*inch
        if booking.standard_qty > 0:
            p.drawString(col2_x, r_cur_y, f"- Standard: {booking.standard_qty}")
            r_cur_y -= 0.15*inch
        if booking.vip_qty > 0:
            p.drawString(col2_x, r_cur_y, f"- VIP: {booking.vip_qty}")
            r_cur_y -= 0.15*inch
            
    # Divider Dots (Vertical line between columns)
    p.setStrokeColor(colors.gray)
    p.setDash(2, 4)
    p.line(t_x + 4.5*inch, content_top_y, t_x + 4.5*inch, t_y + 0.5*inch)
    p.setDash(1, 0)
    
    # Footer Info
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.gray)
    footer_y = t_y - 0.3*inch
    p.drawCentredString(width/2, footer_y, "This ticket is non-transferable. Please bring a valid photo ID for verification.")
    p.drawCentredString(width/2, footer_y - 12, "Scannable Barcode is mandatory for admission.")
    
    p.setFillColor(colors.HexColor("#E11D48"))
    p.drawCentredString(width/2, footer_y - 28, f"Terms & Conditions: All bookings for {exhibition.title} are final.")
    p.drawCentredString(width/2, footer_y - 40, "The exhibition and stall bookings cannot be canceled, and no refunds will be provided.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_exhibition_summary_pdf(bookings, title="Exhibition Bookings Summary"):
    """
    Generates a professional summary report for a list of bookings.
    Returns a BytesIO buffer containing the PDF data.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header Aesthetic
    p.setFillColor(colors.HexColor("#0B50DA"))
    p.rect(0, height - 1.2*inch, width, 1.2*inch, fill=1, stroke=0)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(0.5*inch, height - 0.65*inch, "EXPOSPHERE")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 0.5*inch, height - 0.5*inch, "BOOKING SUMMARY REPORT")
    p.drawRightString(width - 0.5*inch, height - 0.65*inch, f"Generated: {timezone.now().strftime('%b %d, %Y %H:%M')}")
    
    # Sub-header with Title
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(0.5*inch, height - 1.8*inch, title)
    
    # Stats Summary
    total_rev = sum(b.total_price for b in bookings if b.payment_status == 'completed')
    total_bookings = len(bookings)
    stalls_count = sum(b.stalls for b in bookings if b.booking_type == 'stall')
    tickets_count = sum(b.stalls for b in bookings if b.booking_type == 'ticket')
    
    # Draw Stats Boxes
    s_y = height - 2.6*inch
    box_w = 1.6*inch
    box_h = 0.5*inch
    gap = 0.2*inch
    
    def draw_stat(x, label, value, color):
        p.setStrokeColor(colors.HexColor("#E2E8F0"))
        p.setFillColor(colors.white)
        p.roundRect(x, s_y, box_w, box_h, 8, fill=1, stroke=1)
        p.setFillColor(colors.gray)
        p.setFont("Helvetica-Bold", 7)
        p.drawString(x + 0.1*inch, s_y + 0.32*inch, label.upper())
        p.setFillColor(color)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(x + 0.1*inch, s_y + 0.12*inch, str(value))

    draw_stat(0.5*inch, "Total Revenue", f"INR {total_rev:,.0f}", colors.HexColor("#059669"))
    draw_stat(0.5*inch + box_w + gap, "Total Bookings", total_bookings, colors.HexColor("#2563EB"))
    draw_stat(0.5*inch + 2*(box_w + gap), "Stalls Sold", stalls_count, colors.HexColor("#7C3AED"))
    draw_stat(0.5*inch + 3*(box_w + gap), "Tickets Sold", tickets_count, colors.HexColor("#2563EB"))
    
    # Table Data
    data = [["Date", "Booker", "Type", "Qty", "Amount", "Status"]]
    for b in bookings:
        # Format Data
        date_str = b.created_at.strftime('%d %b %y')
        user_str = b.user.get_full_name() or b.user.username
        if len(user_str) > 20: user_str = user_str[:17] + "..."
        
        data.append([
            date_str,
            user_str,
            b.booking_type.capitalize(),
            str(b.stalls),
            f"{b.total_price:,.0f}",
            b.payment_status.upper()
        ])
    
    # Create Table
    table = Table(data, colWidths=[0.8*inch, 2.0*inch, 0.8*inch, 0.6*inch, 1.2*inch, 1.2*inch])
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'), # Align amount to right
        ('ALIGN', (3, 1), (3, -1), 'CENTER'), # Align qty to center
    ])
    
    # Colored rows for status
    for i, b in enumerate(bookings, start=1):
        if b.payment_status == 'completed':
            style.add('TEXTCOLOR', (5, i), (5, i), colors.HexColor("#059669"))
        else:
            style.add('TEXTCOLOR', (5, i), (5, i), colors.HexColor("#D97706"))
            
    table.setStyle(style)
    
    # Draw Table
    t_w, t_h = table.wrap(width - 1.0*inch, height)
    table.drawOn(p, 0.5*inch, s_y - t_h - 0.4*inch)
    
    # Footer
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.gray)
    p.drawString(0.5*inch, 0.4*inch, "Generated via ExpoSphere Organizer Dashboard. Page 1 of 1")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
