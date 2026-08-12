# financeiro/models/conta_pagar.py
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import Fornecedor


class ContaPagar(models.Model):
    """Representa a OBRIGAÇÃO INTEIRA (uma NF, uma conta de luz, uma compra)."""

    class Categoria(models.TextChoices):
        ENERGIA = 'energia', 'Energia elétrica'
        AGUA = 'agua', 'Água'
        TELEFONIA = 'telefonia', 'Telefonia/Internet'
        MATERIA_PRIMA = 'materia_prima', 'Matéria-prima'
        ALUGUEL = 'aluguel', 'Aluguel'
        IMPOSTOS = 'impostos', 'Impostos'
        MANUTENCAO = 'manutencao', 'Manutenção'
        OUTROS = 'outros', 'Outros'

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, related_name='contas_pagar'
    )
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices, blank=True
    )
    descricao = models.CharField(max_length=200)
    numero_documento = models.CharField(max_length=50, blank=True)

    competencia = models.DateField(
        help_text='Mês de referência da despesa (ex: 01/07/2026 para a conta de julho)'
    )
    data_emissao = models.DateField()
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    observacoes = models.TextField(blank=True)

    criado_por = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='contas_pagar_criadas')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conta a Pagar'
        verbose_name_plural = 'Contas a Pagar'
        ordering = ['-data_emissao']

    def __str__(self):
        return f'{self.descricao} — {self.fornecedor} ({self.valor_total})'

    @property
    def valor_pago(self):
        return sum((p.valor_pago for p in self.parcelas.all()), Decimal('0'))


    @property
    def valor_juros_multa(self):
        """Soma de juros/multa pagos em todas as parcelas dessa conta."""
        return sum((p.valor_juros_multa for p in self.parcelas.all()), Decimal('0'))

    @property
    def valor_total_pago(self):
        """Desembolso real: nominal pago + juros/multa pagos."""
        return self.valor_pago + self.valor_juros_multa

    @property
    def saldo_devedor(self):
        return self.valor_total - self.valor_pago

    @property
    def status(self):
        """Status agregado da conta a partir do status_efetivo das parcelas
        (já considera vencimento, sem depender de nada gravado como 'vencido')."""
        statuses = set(p.status_efetivo for p in self.parcelas.all())
        if not statuses:
            return 'aberto'
        if statuses == {'cancelado'}:
            return 'cancelado'
        if statuses <= {'pago', 'cancelado'} and 'pago' in statuses:
            return 'pago'
        if 'vencido' in statuses:
            return 'vencido'
        if 'parcial' in statuses or (len(statuses - {'cancelado'}) > 1):
            return 'parcial'
        return 'aberto'

    @property
    def proximo_vencimento(self):
        """Data da parcela em aberto (não paga, não cancelada) mais próxima. None se não houver."""
        abertas = [
            p.vencimento for p in self.parcelas.all()
            if p.status_efetivo not in ('pago', 'cancelado')
        ]
        return min(abertas) if abertas else None

    def get_status_display(self):
        return dict(ContaPagarParcela.Status.choices).get(self.status, self.status)


class ContaPagarParcela(models.Model):
    class Status(models.TextChoices):
        ABERTO = 'aberto', 'A vencer'
        PARCIAL = 'parcial', 'Pago parcialmente'
        PAGO = 'pago', 'Pago'
        VENCIDO = 'vencido', 'Vencido'  # nunca gravado — só existe via status_efetivo
        CANCELADO = 'cancelado', 'Cancelado'

    conta = models.ForeignKey(ContaPagar, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.PositiveIntegerField(default=1)
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTO)

    class Meta:
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'
        ordering = ['vencimento']
        unique_together = ['conta', 'numero']
        indexes = [models.Index(fields=['status', 'vencimento'])]

    def __str__(self):
        return f'{self.conta.descricao} — {self.numero}/{self.conta.parcelas.count()}'

    @property
    def valor_pago(self):
        return self.pagamentos.aggregate(total=models.Sum('valor_pago'))['total'] or Decimal('0')

    @property
    def valor_juros_multa(self):
        """Soma de juros/multa pagos nessa parcela (pode ter mais de um pagamento parcial)."""
        return self.pagamentos.aggregate(total=models.Sum('juros_multa'))['total'] or Decimal('0')

    @property
    def saldo_devedor(self):
        return self.valor - self.valor_pago

    @property
    def status_efetivo(self):
        """Cruza o status gravado com a data atual: 'aberto' + vencimento passado = 'vencido' na tela,
        sem nunca gravar isso no banco."""
        if self.status == self.Status.ABERTO and self.vencimento < timezone.localdate():
            return self.Status.VENCIDO
        return self.status

    def get_status_efetivo_display(self):
        return dict(self.Status.choices).get(self.status_efetivo, self.status_efetivo)

    def atualizar_status(self):
        """Só transita entre pago/parcial/aberto/cancelado — nunca escreve 'vencido' no banco."""
        if self.status == self.Status.CANCELADO:
            return
        if self.saldo_devedor <= 0:
            novo_status = self.Status.PAGO
        elif self.valor_pago > 0:
            novo_status = self.Status.PARCIAL
        else:
            novo_status = self.Status.ABERTO

        if novo_status != self.status:
            self.status = novo_status
            self.save(update_fields=['status'])


class PagamentoContaPagar(models.Model):
    class Forma(models.TextChoices):
        PIX = 'pix', 'PIX'
        BOLETO = 'boleto', 'Boleto'
        TRANSFERENCIA = 'transferencia', 'Transferência'
        DINHEIRO = 'dinheiro', 'Dinheiro'
        CARTAO = 'cartao', 'Cartão'
        CHEQUE = 'cheque', 'Cheque'

    parcela = models.ForeignKey(ContaPagarParcela, on_delete=models.CASCADE, related_name='pagamentos')
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2)
    juros_multa = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'), blank=True,
        help_text='Valor extra cobrado por atraso (já incluso na conta/boleto), não abate saldo devedor.'
    )
    data_pagamento = models.DateField()
    forma_pagamento = models.CharField(max_length=20, choices=Forma.choices)
    transacao = models.CharField(max_length=100, blank=True)
    observacao = models.CharField(max_length=200, blank=True)

    criado_por = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-data_pagamento']

    @property
    def valor_total_pago(self):
        """Valor efetivamente desembolsado (principal + juros/multa), pra exibição/relatório."""
        return self.valor_pago + self.juros_multa

    def clean(self):
        if self.valor_pago <= 0:
            raise ValidationError('Valor pago deve ser maior que zero.')
        if self.juros_multa < 0:
            raise ValidationError('Juros/multa não pode ser negativo.')
        if self.pk is None and self.valor_pago > self.parcela.saldo_devedor:
            raise ValidationError(f'Valor excede o saldo devedor da parcela ({self.parcela.saldo_devedor}).')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.parcela.atualizar_status()

    def delete(self, *args, **kwargs):
        parcela = self.parcela
        super().delete(*args, **kwargs)
        parcela.atualizar_status()