from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    PERFIL_ADMIN = 'admin'
    PERFIL_ESTOQUE = 'estoque'
    PERFIL_PRODUCAO = 'producao'
    PERFIL_LOJA = 'loja'
    PERFIL_CHOICES = [
        (PERFIL_ADMIN, 'Administrador'),
        (PERFIL_ESTOQUE, 'Operador de Estoque'),
        (PERFIL_PRODUCAO, 'Operador de Produção'),
        (PERFIL_LOJA, 'Operador de Loja'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, verbose_name='Perfil')
    local = models.ForeignKey(
        'core.Local',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Local vinculado'
    )

    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'

    def __str__(self):
        return f'{self.usuario.username} — {self.get_perfil_display()}'