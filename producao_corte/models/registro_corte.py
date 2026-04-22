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


class ItemCorteEntrada(models.Model):
    """Chapas consumidas no corte — baixa no estoque."""
    registro = models.ForeignKey(
        RegistroCorte, on_delete=models.CASCADE, related_name='entradas'
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, verbose_name='Chapa/Material'
    )
    quantidade = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Quantidade'
    )

    class Meta:
        verbose_name = 'Material Utilizado'
        verbose_name_plural = 'Materiais Utilizados'


class ItemCorteSaida(models.Model):
    """Produtos cortados — ainda não montados."""
    STATUS_AGUARDANDO = 'aguardando'
    STATUS_MONTADO = 'montado'
    STATUS_CHOICES = [
        (STATUS_AGUARDANDO, 'Aguardando Montagem'),
        (STATUS_MONTADO, 'Montado'),
    ]

    registro = models.ForeignKey(
        RegistroCorte, on_delete=models.CASCADE, related_name='saidas'
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, verbose_name='Produto Cortado'
    )
    quantidade = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Quantidade'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_AGUARDANDO, verbose_name='Status'
    )

    class Meta:
        verbose_name = 'Produto Cortado'
        verbose_name_plural = 'Produtos Cortados'