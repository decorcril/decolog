from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError


class Movimentacao(models.Model):

    TIPO_ENTRADA = 'entrada'
    TIPO_SAIDA = 'saida'
    TIPO_TRANSFERENCIA = 'transferencia'
    TIPO_AJUSTE = 'ajuste'

    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SAIDA, 'Saída'),
        (TIPO_TRANSFERENCIA, 'Transferência'),
        (TIPO_AJUSTE, 'Ajuste'),
    ]

    MOTIVO_CHOICES = [
        ('compra', 'Compra'),
        ('venda', 'Venda'),
        ('perda', 'Perda / Avaria'),
        ('uso_interno', 'Uso Interno'),
        ('troca', 'Troca'),
        ('publicidade', 'Publicidade'),
        ('reposicao', 'Reposição'),
        ('manutencao', 'Manutenção'),
        ('transferencia', 'Transferência'),
        ('ajuste', 'Ajuste'),
        ('outro', 'Outro'),
    ]

    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='movimentacoes',
        verbose_name='Produto'
    )
    local = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='movimentacoes',
        verbose_name='Local'
    )
    local_destino = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='movimentacoes_destino',
        null=True, blank=True,
        verbose_name='Local de Destino'
    )
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES,
        verbose_name='Tipo'
    )
    motivo = models.CharField(
        max_length=20, choices=MOTIVO_CHOICES,
        blank=True, verbose_name='Motivo'
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Quantidade'
    )
    fornecedor = models.ForeignKey(
        'core.Fornecedor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Fornecedor'
    )
    registro_corte = models.ForeignKey(
        'producao_corte.RegistroCorte',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimentacoes',
        verbose_name='Registro de Corte'
    )
    nota_fiscal = models.CharField(
        max_length=50, blank=True,
        verbose_name='Nota Fiscal'
    )
    observacao = models.TextField(
        blank=True, verbose_name='Observação'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Usuário'
    )
    data_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data/Hora'
    )

    class Meta:
        verbose_name = 'Movimentação'
        verbose_name_plural = 'Movimentações'
        ordering = ['-data_hora']

    def __str__(self):
        return (
            f'{self.get_tipo_display()} — {self.produto.nome} '
            f'({self.quantidade}) — {self.data_hora.strftime("%d/%m/%Y %H:%M")}'
        )

    def clean(self):
        if self.local and self.produto:
            if self.local.is_loja and self.produto.is_materia_prima:
                raise ValidationError('Loja não pode receber matéria-prima.')

        if self.tipo == self.TIPO_TRANSFERENCIA:
            if not self.local_destino:
                raise ValidationError('Transferência requer local de destino.')
            if self.local == self.local_destino:
                raise ValidationError('Origem e destino não podem ser iguais.')

        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError('Quantidade deve ser maior que zero.')

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            self._aplicar_movimentacao()

    def _aplicar_movimentacao(self):
        from estoque.models import Estoque

        saldo = Estoque.get_or_create_saldo(self.produto, self.local)

        if self.tipo == self.TIPO_ENTRADA:
            saldo.adicionar(self.quantidade)
        elif self.tipo == self.TIPO_SAIDA:
            saldo.subtrair(self.quantidade)
        elif self.tipo == self.TIPO_AJUSTE:
            saldo.quantidade = self.quantidade
            saldo.save(update_fields=['quantidade', 'atualizado_em'])
        elif self.tipo == self.TIPO_TRANSFERENCIA:
            saldo.subtrair(self.quantidade)
            saldo_destino = Estoque.get_or_create_saldo(self.produto, self.local_destino)
            saldo_destino.adicionar(self.quantidade)