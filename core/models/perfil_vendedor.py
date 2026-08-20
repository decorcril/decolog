from django.db import models
from django.contrib.auth.models import User


class PerfilVendedor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='perfil_vendedor', verbose_name='Usuário'
    )
    loja = models.ForeignKey(
        'core.Local', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vendedores', verbose_name='Loja'
    )

    class Meta:
        verbose_name        = 'Perfil do Vendedor'
        verbose_name_plural  = 'Perfis dos Vendedores'

    def __str__(self):
        loja_nome = self.loja.nome if self.loja else 'Sem loja definida'
        return f'{self.user.username} — {loja_nome}'