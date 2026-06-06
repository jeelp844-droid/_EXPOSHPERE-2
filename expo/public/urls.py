from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('work/',views.Work,name='work'),
    path('register/', views.register, name="register"),
    path('login/', views.delogin, name="delogin"),
    path('logout/', views.user_logout, name="logout"),
    
    path('exhibition/',views.exhibition,name='exhibition'),
    path('exhibition/<int:id>/', views.exhibition_detail, name='exhibition_detail'),
    path('exhibition/<int:id>/book-tickets/', views.book_tickets, name='book_tickets'),
    path('exhibition/<int:id>/book-stall/', views.book_stall, name='book_stall'),
    path('exhibition/<int:id>/send-enquiry/', views.send_enquiry, name='send_enquiry'),
    path('load-cities/',views.load_cities,name="load_cities"),  
    path('forgot-password/', views.forgot_password, name="forgot_password"),
    path('reset-password/<int:id>/', views.reset_password, name="reset_password"),
    path('booking/<int:booking_id>/success/', views.booking_success, name="booking_success"),
    path('booking/<int:booking_id>/download-pass/', views.download_pass, name="download_pass"),
    path('stall-details/<int:stall_id>/', views.stall_details, name='stall_details'),
    path('set-social-role/', views.set_social_role, name='set_social_role'),
]