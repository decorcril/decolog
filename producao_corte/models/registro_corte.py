from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from produtos.models import Produto


class RegistroCorte(models.Model):
    data = models.DateField(verbose_name='Data')
    operador = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Operador'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de Corte'
        verbose_name_plural = 'Registros de Corte'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'Corte {self.data} — {self.operador.get_full_name() or self.operador.username}'

    def clean(self):
        if self.data and self.data > timezone.localdate():
            raise ValidationError('A data não pode ser no futuro.')


class ItemCorte(models.Model):
    """Uma chapa utilizada no corte, com seus produtos cortados."""
    registro = models.ForeignKey(
        RegistroCorte, on_delete=models.CASCADE, related_name='itens'
    )
    chapa = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        limit_choices_to={'categoria__in': ['chapa', 'insumo']},
        verbose_name='Chapa / Material'
    )
    quantidade_chapa = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Quantidade'
    )

    class Meta:
        verbose_name = 'Item de Corte'
        verbose_name_plural = 'Itens de Corte'


class ProdutoCortado(models.Model):
    """Produto cortado a partir de uma chapa específica."""
    item_corte = models.ForeignKey(
        ItemCorte, on_delete=models.CASCADE, related_name='produtos_cortados'
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        limit_choices_to={'categoria': 'produto_final'},
        verbose_name='Produto Cortado'
    )
    quantidade = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Quantidade'
    )
    status = models.CharField(
        max_length=20,
        choices=[('aguardando', 'Aguardando Montagem'), ('montado', 'Montado')],
        default='aguardando',
        verbose_name='Status'
    )

    class Meta:
        verbose_name = 'Produto Cortado'
        verbose_name_plural = 'Produtos Cortados'