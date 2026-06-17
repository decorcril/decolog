import os
from django.db import models
from django.contrib.auth.models import User
from vendas.models.pedido import Pedido


class Envio(models.Model):
    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE,
        related_name='envio', verbose_name='Pedido'
    )
    arquivo = models.FileField(
        upload_to='envios/%Y/%m/',
        blank=True, null=True,
        verbose_name='Comprovante de Envio'
    )
    rastreio = models.CharField(
        max_length=100, blank=True,
        verbose_name='Código de Rastreio'
    )
    transportadora = models.CharField(
        max_length=100, blank=True,
        verbose_name='Transportadora'
    )
    criado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='Registrado por'
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name        = 'Envio'
        verbose_name_plural = 'Envios'

    def __str__(self):
        return f'Envio — Pedido {self.pedido.numero}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        pedido = self.pedido
        if pedido.status == Pedido.Status.PICKING:
            pedido.status = Pedido.Status.SHIPPED
            pedido.save(update_fields=['status', 'atualizado_em'])

    def delete(self, *args, **kwargs):
        if self.arquivo and os.path.isfile(self.arquivo.path):
            os.remove(self.arquivo.path)
        super().delete(*args, **kwargs)