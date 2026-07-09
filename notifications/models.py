from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from organizations.models import Unit

class Alert(models.Model):
    TYPE_CHOICES = (
        ('ESTOQUE_BAIXO', 'Estoque abaixo do Mínimo'),
        ('LOTE_VENCIMENTO', 'Lote Próximo do Vencimento'),
        ('LOTE_VENCIDO', 'Lote Vencido'),
        ('CA_VENCIMENTO', 'C.A. Próximo do Vencimento'),
        ('CA_VENCIDO', 'C.A. Vencido'),
        ('CA_NAO_VERIFICADO', 'C.A. não verificado ou desatualizado'),
        ('TROCA_BREVE', 'EPI de Colaborador próximo da troca'),
        ('TROCA_VENCIDA', 'EPI de Colaborador com troca vencida'),
        ('TRANSFERENCIA_PENDENTE', 'Transferência pendente de recebimento'),
        ('FALTA_CIENCIA', 'Entrega sem ciência/assinatura'),
        ('DIVERGENCIA_ESTOQUE', 'Divergência de estoque'),
    )

    SEVERITY_CHOICES = (
        ('INFO', 'Informação'),
        ('WARNING', 'Aviso / Atenção'),
        ('CRITICAL', 'Crítico / Urgente'),
    )

    STATUS_CHOICES = (
        ('NOVO', 'Novo'),
        ('LIDO', 'Lido'),
        ('RESOLVIDO', 'Resolvido'),
    )

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='alerts', blank=True, null=True, verbose_name="Unidade")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts', blank=True, null=True, verbose_name="Usuário Destinatário")
    
    alert_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Tipo de Alerta")
    severity = models.CharField(max_length=15, choices=SEVERITY_CHOICES, default='INFO', verbose_name="Gravidade")
    
    title = models.CharField(max_length=255, verbose_name="Título do Alerta")
    message = models.TextField(verbose_name="Mensagem")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NOVO', verbose_name="Status")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Resolvido em")

    # Generic relation link (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} - {self.get_status_display()}"
