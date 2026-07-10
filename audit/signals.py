from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .models import log_action

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT') if request else None
    log_action(
        user=user,
        action="Login bem-sucedido",
        model_name="CustomUser",
        object_id=user.id,
        before=None,
        after=None,
        ip=ip,
        ua=ua
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT') if request else None
        log_action(
            user=user,
            action="Logout",
            model_name="CustomUser",
            object_id=user.id,
            before=None,
            after=None,
            ip=ip,
            ua=ua
        )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT') if request else None
    username = credentials.get('username', 'Desconhecido')
    log_action(
        user=None,
        action=f"Tentativa de login falha para usuario: {username}",
        model_name="CustomUser",
        object_id=None,
        before=None,
        after=None,
        ip=ip,
        ua=ua
    )
