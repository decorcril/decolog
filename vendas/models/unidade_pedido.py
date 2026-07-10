import secrets
from django.db import models


class UnidadePedido(models.Model):
    item         = models.ForeignKey(
        'vendas.ItemPedido',
        on_delete=models.CASCADE,
        related_name='unidades',
        verbose_name='Item do Pedido'
    )
    numero       = models.PositiveIntegerField(verbose_name='Número da Unidade')
    token        = models.CharField(max_length=64, unique=True, blank=True, verbose_name='Token')

    # ── Montagem ──
    montada      = models.BooleanField(default=False, verbose_name='Montada')
    montada_em   = models.DateTimeField(null=True, blank=True, verbose_name='Montada em')
    montada_por  = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='unidades_montadas',
        verbose_name='Montada por'
    )

    # ── Separação ──
    separada     = models.BooleanField(default=False, verbose_name='Separada')
    separada_em  = models.DateTimeField(null=True, blank=True, verbose_name='Separada em')
    separada_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='unidades_separadas',
        verbose_name='Separada por'
    )

    criado_em    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Unidade do Pedido'
        verbose_name_plural = 'Unidades do Pedido'
        ordering            = ['item', 'numero']
        unique_together     = ('item', 'numero')

    def __str__(self):
        return f'{self.item.produto.nome} — Unidade {self.numero}/{self.item.quantidade}'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)