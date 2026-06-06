from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from public.models import register as RegisterModel
from django.shortcuts import resolve_url, redirect
from django.contrib import messages
from django.contrib.auth.models import User

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user and creates the custom register record.
        Handles linking existing register records by email.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Get role from session (set during registration button click)
        # Default to 'Visitor' if not set (direct login)
        role = request.session.get('social_role', 'Visitor')
        full_name = sociallogin.account.extra_data.get('name', user.get_full_name() or user.username)
        
        # Check if register record already exists for this user
        reg = RegisterModel.objects.filter(user=user).first()
        
        if not reg:
            # Fallback: check if a record with the same email exists (manual registration previously)
            reg = RegisterModel.objects.filter(email=user.email).first()
            if reg:
                # Link existing manual profile to this social user
                reg.user = user
                reg.full_name = full_name # Update to latest from Google
                reg.save()
            else:
                # Create fresh profile
                RegisterModel.objects.create(
                    user=user,
                    full_name=full_name,
                    email=user.email,
                    username=user.username,
                    role=role,
                    is_approved=(role == 'Visitor')
                )
        
        # Notification for Organizer
        if reg and reg.role == 'Organizer' and not reg.is_approved:
             messages.info(request, "Your Organizer account is awaiting administrator approval.")
        
        return user

    def get_login_redirect_url(self, request):
        """
        Redirects users to the central dashboard redirector after login.
        """
        return resolve_url('dashboard_redirect')

    def on_authentication_error(self, request, provider_id, error, exception, extra_context):
        """
        Avoid the default "Third-Party Login Failure" page.
        Redirect back to login with a user-friendly message.
        """
        messages.error(request, f"Connection unsuccessful: {error or 'An error occurred during Google login'}. Please try again.")
        return redirect('delogin')
