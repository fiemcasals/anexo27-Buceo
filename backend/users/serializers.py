from dj_rest_auth.serializers import PasswordResetSerializer as DefaultPasswordResetSerializer
from allauth.account.utils import user_pk_to_url_str
from django.conf import settings


def frontend_url_generator(request, user, temp_key):
    uid = user_pk_to_url_str(user)
    return f"{settings.FRONTEND_URL}/password-reset/{uid}/{temp_key}"


class CustomPasswordResetSerializer(DefaultPasswordResetSerializer):
    def get_email_options(self):
        return {'url_generator': frontend_url_generator}
