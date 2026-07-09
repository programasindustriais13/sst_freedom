from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ADMIN = 'ADMIN'
    TECNICO_SST = 'TECNICO_SST'
    ALMOXARIFE = 'ALMOXARIFE'
    
    PROFILE_CHOICES = (
        (ADMIN, 'Administrador'),
        (TECNICO_SST, 'Técnico de Segurança do Trabalho'),
        (ALMOXARIFE, 'Almoxarife'),
    )
    
    profile_type = models.CharField(
        max_length=20,
        choices=PROFILE_CHOICES,
        default=TECNICO_SST,
        verbose_name="Tipo de Perfil"
    )
    
    units = models.ManyToManyField(
        'organizations.Unit',
        blank=True,
        related_name='users',
        verbose_name="Unidades Autorizadas"
    )
    
    def is_admin(self):
        return self.profile_type == self.ADMIN or self.is_superuser
        
    def is_tecnico(self):
        return self.profile_type == self.TECNICO_SST or self.is_superuser
        
    def is_almoxarife(self):
        return self.profile_type == self.ALMOXARIFE or self.is_superuser

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
