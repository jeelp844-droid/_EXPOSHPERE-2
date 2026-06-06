from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from .models import register as RegisterModel
from django.contrib.auth.models import User

@receiver(user_signed_up)
def populate_register_model(request, user, **kwargs):
    """
    This signal is triggered when a user signs up via allauth (social or regular).
    We use it to ensure a 'register' (Profile) record exists for social users.
    """
    # Check if a register record already exists
    if not RegisterModel.objects.filter(user=user).exists():
        # User is likely from social login
        full_name = user.get_full_name() or user.username
        
        # Get role from session (set during registration page selection)
        role = request.session.get('social_role', 'Visitor')
        # Validate role
        if role not in ['Visitor', 'Organizer']:
            role = 'Visitor'
            
        RegisterModel.objects.create(
            user=user,
            full_name=full_name,
            email=user.email,
            username=user.username,
            role=role, 
            is_approved=(role == 'Visitor') # Visitors are auto-approved
        )
        
        # Clean up session
        if 'social_role' in request.session:
            del request.session['social_role']
