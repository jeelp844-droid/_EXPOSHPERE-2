from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# Contact
class Contact(models.Model):
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    is_replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

# Register
class register(models.Model):
    ROLE_CHOICES = [
        ('Visitor', 'Visitor'),
        ('Organizer', 'Organizer'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Visitor')
    is_approved = models.BooleanField(default=False)
    role_upgrade_pending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

# Exhibition Page
 
# CATEGORY
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='category', help_text="Material Symbol name")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self): return self.name

# COUNTRY
class Country(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

# CITY
class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    def __str__(self): return f"{self.name} - {self.country.name}"

# EXHIBITION
class Exhibition(models.Model):
    STATUS_CHOICES = [
        ('pending','Pending'),
        ('approved','Approved'),
        ('rejected','Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='exhibitions/', null=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.CharField(max_length=200, default='') # <--- New field
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    location = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True) # <--- New field
    end_time = models.TimeField(null=True, blank=True) # <--- New field
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stall_price = models.DecimalField(max_digits=8, decimal_places=2, default=0) # <--- New field
    total_stalls = models.IntegerField(default=0) # <--- New field
    total_tickets = models.IntegerField(default=0) # <--- New field
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending') # Default status is pending
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# Status
    @property
    def dynamic_status(self):
        from django.utils import timezone
        now = timezone.now()
        today = now.date()
        current_year = now.year
        current_month = now.month
        
        # 1. If end_date has passed, it's Complete
        if self.end_date < today:
            return "Complete"
            
        # 2. Check based on month and year (as per original requirements)
        if (self.start_date.year, self.start_date.month) < (current_year, current_month):
            return "Complete"
        elif (self.start_date.year, self.start_date.month) == (current_year, current_month):
            return "Ongoing"
        else:
            return "Upcoming"

class Stall(models.Model):
    STALL_TYPES = [
        ('small', 'Small (₹)'),
        ('large', 'Large (₹₹)'),
    ]
    STALL_STATUS = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('maintenance', 'Maintenance'),
    ]
    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE, related_name='stalls_list')
    stall_number = models.CharField(max_length=10)
    stall_type = models.CharField(max_length=10, choices=STALL_TYPES, default='small')
    status = models.CharField(max_length=20, choices=STALL_STATUS, default='available')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dimensions = models.CharField(max_length=50, default='3m x 3m (9sqm)')
    position = models.CharField(max_length=100, default='Standard')
    amenities = models.TextField(blank=True, default='High-speed WiFi (100Mbps), Dual 220V Power Outlets, 2 Chairs & 1 Information Desk, 3 Spotlight Fixtures')
    image = models.ImageField(upload_to='stalls/', null=True, blank=True)
    
    class Meta:
        unique_together = ('exhibition', 'stall_number')

    def __str__(self):
        return f"{self.stall_number} - {self.exhibition.title}"

# BOOKING
class Booking(models.Model):
    BOOKING_TYPES = [
        ('ticket', 'Ticket'),
        ('stall', 'Stall'),
    ]
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE)
    stalls = models.IntegerField(default=1) # Can represent quantity for both
    stall_instance = models.ForeignKey(Stall, on_delete=models.SET_NULL, null=True, blank=True)
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPES, default='ticket')
    student_qty = models.IntegerField(default=0)
    standard_qty = models.IntegerField(default=0)
    vip_qty = models.IntegerField(default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    student_id_proof = models.FileField(upload_to='student_ids/', blank=True, null=True)
    
    # Stall Details (Step 3)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    representative_name = models.CharField(max_length=200, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    stall_description = models.TextField(blank=True, null=True)
    
    # Additional Equipment
    has_extra_chairs = models.BooleanField(default=False)
    has_spotlight = models.BooleanField(default=False)
    has_power_strip = models.BooleanField(default=False)
    has_tv_display = models.BooleanField(default=False)
    has_brochure_stand = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.exhibition.title} ({self.stalls} stalls)"

# ENQUIRY
class Enquiry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    is_replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# USER PROFILE
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    gov_id_type = models.CharField(max_length=50, blank=True, default='')
    gov_id_number = models.CharField(max_length=50, blank=True, default='')
    gov_id_upload = models.FileField(upload_to='gov_id/', null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    def __str__(self):
        return self.user.username

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('visitor', 'Visitor'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
