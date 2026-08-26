from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from clientes.models import Cliente
from produtos.models import Produto
from core.models.sequence import Sequence


class Orcamento(models.Model):

    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Em elaboração'
        APPROVED = 'approved', 'Aprovado'
        REJECTED = 'rejected', 'Rejeitado'
        EXPIRED  = 'expired',  'Expirado'

    class PrazoConfeccao(models.TextChoices):
        DIAS_15        = "15",     "15 dias"
        DIAS_20        = "20",     "20 dias"
        DIAS_25        = "25",     "25 dias"
        DIAS_30        = "30",     "30 dias"
        PRONTA_ENTREGA = "pronta", "À Pronta Entrega"

    numero               = models.CharField(max_length=20, unique=True, editable=False)
    cliente              = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='orcamentos')
    tipo_venda           = models.CharField(max_length=20, choices=[
        ('direct',      'Venda direta'),
        ('replacement', 'Reposição'),
        ('exchange',    'Troca'),
        ('maintenance', 'Manutenção'),
        ('advertising', 'Publicidade'),
        ('comodato',    'Comodato'),
    ])
    condicao_pagamento   = models.CharField(max_length=100, blank=True)
    contato              = models.CharField(max_length=100, blank=True)
    transportadora       = models.CharField(max_length=100, blank=True)
    frete                = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prazo_confeccao      = models.CharField(
        max_length=10, choices=PrazoConfeccao.choices, blank=True,
        verbose_name='Prazo de Confecção'
    )
    urgente              = models.BooleanField(default=False, verbose_name='Urgente')
    total_desconto       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacoes          = models.TextField(blank=True)
    observacoes_internas = models.TextField(blank=True)
    status               = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    validade             = models.DateField(null=True, blank=True)
    pedido               = models.OneToOneField(
        'vendas.Pedido', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orcamento_origem'
    )
    criado_por    = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orcamentos')
    criado_em     = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Orçamento'
        verbose_name_plural = 'Orçamentos'

    def __str__(self):
        return f'{self.numero} — {self.cliente.nome}'

    def save(self, *args, **kwargs):
        if not self.numero:
            n = Sequence.next_formatted('orcamento', start=1)
            self.numero = f'ORC-{n}'
        if not self.validade:
            self.validade = (timezone.now() + timedelta(days=10)).date()
        super().save(*args, **kwargs)

    @property
    def total_produtos(self):
        return sum(i.subtotal for i in self.itens.all())

    @property
    def total_geral(self):
        return max(self.total_produtos - self.total_desconto + self.frete, Decimal('0'))

    @property
    def expirado(self):
        return self.status == self.Status.DRAFT and timezone.now().date() > self.validade


class ItemOrcamento(models.Model):
    orcamento      = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    produto        = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade     = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item de Orçamento'

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome}'

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario