from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"

    def get_reset_password_url(self, request, user, token):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return f"{settings.FRONTEND_URL}/password-reset/{uid}/{token}"

    def send_mail(self, template_prefix, email, context):
        """El correo de recuperar la contraseña sale igual que el aviso de un
        estudio rechazado (`api.correo`): texto plano en castellano, sin el
        prefijo del sitio y desde la misma casilla (`DEFAULT_FROM_EMAIL`).

        dj-rest-auth manda ese correo por acá con una dirección del backend;
        se arma de nuevo la del frontend, que es la pantalla que pide la clave."""
        if template_prefix != 'account/email/password_reset_key':
            return super().send_mail(template_prefix, email, context)
        enlace = self.get_reset_password_url(
            context.get('request'), context['user'], context['token'])
        send_mail(
            subject='Recuperación de contraseña',
            message=(
                'Se pidió restablecer la contraseña de tu cuenta.\n'
                '\n'
                'Para elegir una contraseña nueva, ingresar a este enlace:\n'
                f'{enlace}\n'
                '\n'
                'Si no pediste el cambio, ignorá este correo: tu contraseña '
                'sigue siendo la misma.\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[email],
        )
