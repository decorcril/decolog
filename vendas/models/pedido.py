from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib.auth.models import User
from clientes.models import Cliente
from produtos.models import Produto

TWO = Decimal("0.01")

FREE_SALE_TYPES = {"exchange", "maintenance", "advertising", "replacement"}


class Pedido(models.Model):

    class Status(models.TextChoices):
        OPEN          = "open",          "Em aberto"
        IN_PRODUCTION = "in_production", "Em Produção"
        PICKING       = "picking",       "Em Separação"
        SHIPPED       = "shipped",       "Enviado"
        DELIVERED     = "delivered",     "Entregue"
        CANCELED      = "canceled",      "Cancelado"

    class TipoVenda(models.TextChoices):
        DIRECT      = "direct",      "Venda direta"
        REPLACEMENT = "replacement", "Reposição"
        EXCHANGE    = "exchange",    "Troca"
        MAINTENANCE = "maintenance", "Manutenção"
        ADVERTISING = "advertising", "Publicidade"
        COMODATO    = "comodato",    "Comodato"

    # Identificação
    numero = models.CharField(
        max_length=10, unique=True, blank=True,
        verbose_name='Número do Pedido', db_index=True
    )

    # Relacionamentos
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='pedidos', verbose_name='Cliente'
    )
    criado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='pedidos_criados', verbose_name='Criado por'
    )
    responsavel = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='pedidos_responsavel',
        null=True, blank=True, verbose_name='Responsável'
    )

    # Status e tipo
    status    = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.OPEN, db_index=True,
        verbose_name='Status'
    )
    tipo_venda = models.CharField(
        max_length=20, choices=TipoVenda.choices,
        blank=True, verbose_name='Tipo de Venda'
    )

    # Dados comerciais
    pedido_cliente    = models.CharField(max_length=100, blank=True, verbose_name='Pedido do Cliente')
    condicao_pagamento = models.CharField(max_length=100, blank=True, verbose_name='Condição de Pagamento')
    contato           = models.CharField(max_length=100, blank=True, verbose_name='Contato')
    transportadora    = models.CharField(max_length=50, blank=True, verbose_name='Transportadora')
    frete             = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Frete')
    percentual_entrada = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        blank=True, verbose_name='Entrada (%)',
        help_text='Percentual mínimo para liberar produção'
    )
    data_entrega = models.DateField(null=True, blank=True, verbose_name='Data de Entrega')

    # Observações
    observacoes          = models.TextField(blank=True, verbose_name='Observações')
    observacoes_internas = models.TextField(blank=True, verbose_name='Observações Internas')

    # Totais
    total_produtos = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Produtos')
    total_desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Desconto')
    total_impostos = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Impostos')
    total_geral    = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Geral')

    # Datas
    criado_em     = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering            = ['-criado_em']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'Pedido {self.numero} — {self.cliente.nome}'

    def save(self, *args, **kwargs):
        if not self.pk and not self.numero:
            from core.models import Sequence
            self.numero = Sequence.next_formatted('pedido', start=3000)
        if not self.responsavel:
            self.responsavel = self.criado_por
        super().save(*args, **kwargs)

    # ── Properties ──

    @property
    def is_free_sale(self) -> bool:
        return self.tipo_venda in FREE_SALE_TYPES

    @property
    def total_pago(self) -> Decimal:
        result = self.pagamentos.aggregate(total=models.Sum('valor'))['total']
        return (result or Decimal("0.00")).quantize(TWO)

    @property
    def saldo_restante(self) -> Decimal:
        return max(Decimal("0.00"), self.total_geral - self.total_pago)

    @property
    def valor_entrada(self) -> Decimal:
        return (self.total_geral * self.percentual_entrada / 100).quantize(TWO)

    # ── Status automático ──

    def sync_status(self):
        protected = {
            self.Status.PICKING,
            self.Status.SHIPPED,
            self.Status.DELIVERED,
            self.Status.CANCELED,
        }
        if self.status in protected:
            return

        if self.is_free_sale:
            new_status = self.Status.IN_PRODUCTION
        else:
            new_status = self.Status.IN_PRODUCTION if self.pagamentos.exists() else self.Status.OPEN

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status', 'atualizado_em'])


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='itens', verbose_name='Pedido'
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        related_name='itens_pedido', verbose_name='Produto'
    )
    quantidade    = models.PositiveIntegerField(default=1, verbose_name='Quantidade')
    preco_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Preço Unitário'
    )

    class Meta:
        verbose_name        = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        ordering            = ['id']

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome} → {self.pedido.numero}'

    @property
    def subtotal(self) -> Decimal:
        return (self.preco_unitario * self.quantidade).quantize(TWO, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_totais()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        self._sync_totais(pedido)

    def _sync_totais(self, pedido=None):
        pedido = pedido or self.pedido
        total = sum(
            (i.preco_unitario * i.quantidade).quantize(TWO)
            for i in pedido.itens.all()
        )
        pedido.total_produtos = total
        pedido.total_geral = (
            total - pedido.total_desconto + pedido.total_impostos + pedido.frete
        ).quantize(TWO)
        pedido.save(update_fields=['total_produtos', 'total_geral', 'atualizado_em'])