from django.db import models
from django.contrib.auth.models import User


class PrecoProduto(models.Model):
    produto = models.OneToOneField(
        'produtos.Produto',
        on_delete=models.CASCADE,
        related_name='preco',
        verbose_name='Produto'
    )
    preco_venda = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Preço de Venda'
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Atualizado por'
    )

    class Meta:
        verbose_name = 'Preço'
        verbose_name_plural = 'Preços'

    def __str__(self):
        return f'{self.produto.nome} — R$ {self.preco_venda}'