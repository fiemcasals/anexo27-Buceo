from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"

    def get_reset_password_url(self, request, user, token):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return f"{settings.FRONTEND_URL}/password-reset/{uid}/{token}"
