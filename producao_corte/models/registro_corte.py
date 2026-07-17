from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from produtos.models import Produto


class RegistroCorte(models.Model):
    pedido     = models.ForeignKey(
        'vendas.Pedido', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='registros_corte',
        verbose_name='Pedido'
    )
    data       = models.DateField(verbose_name='Data')
    operador   = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Operador'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')
    criado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Registro de Corte'
        verbose_name_plural = 'Registros de Corte'
        ordering            = ['-data', '-criado_em']

    def __str__(self):
        if self.pedido:
            return f'Corte {self.data} — Pedido {self.pedido.numero} — {self.operador.get_full_name() or self.operador.username}'
        return f'Corte {self.data} — {self.operador.get_full_name() or self.operador.username}'

    def clean(self):
        if self.data and self.data > timezone.localdate():
            raise ValidationError('A data não pode ser no futuro.')


class ItemCorte(models.Model):
    registro         = models.ForeignKey(
        RegistroCorte, on_delete=models.CASCADE, related_name='itens'
    )
    chapa            = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        limit_choices_to={'categoria__in': ['chapa', 'insumo']},
        verbose_name='Chapa / Material'
    )
    quantidade_chapa = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Quantidade'
    )

    class Meta:
        verbose_name        = 'Item de Corte'
        verbose_name_plural = 'Itens de Corte'


class ProdutoCortado(models.Model):
    item_corte   = models.ForeignKey(
        ItemCorte, on_delete=models.CASCADE, related_name='produtos_cortados'
    )
    produto      = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        limit_choices_to={'categoria': 'produto_final'},
        verbose_name='Produto Cortado'
    )
    pedido       = models.ForeignKey(
        'vendas.Pedido', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='produtos_cortados'
    )
    status       = models.CharField(
        max_length=20,
        choices=[
            ('aguardando', 'Aguardando Montagem'),
            ('montado',    'Montado'),
            ('separado',   'Separado'),
            ('enviado',    'Enviado'),
        ],
        default='aguardando',
        verbose_name='Status'
    )
    token        = models.CharField(
        max_length=64, unique=True, blank=True,
        verbose_name='Token'
    )
    observacao   = models.TextField(blank=True, verbose_name='Observação')
    cortada_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pecas_cortadas',
        verbose_name='Cortada por'
    )
    montada_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pecas_montadas',
        verbose_name='Montada por'
    )
    montada_em   = models.DateTimeField(null=True, blank=True, verbose_name='Montada em')
    separada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pecas_separadas',
        verbose_name='Separada por'
    )
    separada_em  = models.DateTimeField(null=True, blank=True, verbose_name='Separada em')

    class Meta:
        verbose_name        = 'Peça Cortada'
        verbose_name_plural = 'Peças Cortadas'

    def __str__(self):
        return f'{self.produto.nome} — {self.token[:8] if self.token else "sem token"}'

    def save(self, *args, **kwargs):
        import secrets
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)