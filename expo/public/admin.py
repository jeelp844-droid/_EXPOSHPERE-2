from django.contrib import admin
from .models import Country, City, Exhibition, Contact, register, Stall, Booking, Category, Enquiry

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name',)

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('user', 'exhibition', 'subject', 'created_at')
    search_fields = ('user__username', 'exhibition__title', 'subject')

# Register your models here.

@admin.register(register)
class registerAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'mobile', 'role')
    list_filter = ('role',)
    search_fields = ('username', 'full_name', 'email', 'mobile')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('fname', 'lname', 'email', 'subject')
    search_fields = ('fname', 'lname', 'email', 'subject')

@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'status', 'is_approved', 'start_date', 'end_date')
    list_filter = ('category', 'status', 'is_approved')
    search_fields = ('title', 'description', 'venue')

@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_display = ('stall_number', 'exhibition', 'stall_type', 'status', 'price')
    list_filter = ('stall_type', 'status')
    search_fields = ('stall_number', 'exhibition__title')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'exhibition', 'booking_type', 'stalls', 'total_price', 'status', 'created_at')
    list_filter = ('booking_type', 'status')
    search_fields = ('user__username', 'exhibition__title')

admin.site.register(Country)
admin.site.register(City)