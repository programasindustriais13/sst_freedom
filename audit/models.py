from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsável")
    action = models.CharField(max_length=255, verbose_name="Ação Executada")
    model_name = models.CharField(max_length=100, verbose_name="Nome da Entidade")
    object_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID do Objeto")
    
    changes_before = models.TextField(blank=True, null=True, verbose_name="Valores Anteriores")
    changes_after = models.TextField(blank=True, null=True, verbose_name="Valores Posteriores")
    
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Endereço IP")
    user_agent = models.CharField(max_length=255, blank=True, null=True, verbose_name="Navegador/User Agent")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Registro de Auditoria"
        verbose_name_plural = "Registros de Auditoria"
        ordering = ['-created_at']

    def __str__(self):
        actor = self.user.username if self.user else "Sistema"
        return f"{self.created_at.strftime('%d/%m/%Y %H:%M:%S')} - {actor}: {self.action} em {self.model_name}"


def log_action(user, action, model_name, object_id=None, before=None, after=None, ip=None, ua=None):
    """
    Função utilitária para gravar registros de auditoria imutáveis.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else None,
        changes_before=str(before) if before else None,
        changes_after=str(after) if after else None,
        ip_address=ip,
        user_agent=ua
    )


def log_audit(request, action, model_name, object_id=None, before=None, after=None):
    """
    Grava um log de auditoria associando o usuário autenticado, IP e User Agent do request.
    """
    user = request.user if request and request.user.is_authenticated else None
    ip = None
    ua = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT')
        
    return log_action(user, action, model_name, object_id, before, after, ip, ua)
