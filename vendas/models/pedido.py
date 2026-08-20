from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from clientes.models import Cliente
from produtos.models import Produto
import secrets


TWO = Decimal("0.01")

FREE_SALE_TYPES = {"exchange", "maintenance", "advertising", "replacement", "comodato"}


def _criar_unidades_insumos(pedido):
    """Cria UnidadePedido automaticamente para itens do tipo insumo."""
    from vendas.models.unidade_pedido import UnidadePedido
    for item in pedido.itens.select_related('produto').all():
        if item.produto.categoria == 'insumo':
            ja_existentes = item.unidades.count()
            for n in range(item.quantidade):
                numero = ja_existentes + n + 1
                if numero <= item.quantidade:
                    UnidadePedido.objects.get_or_create(
                        item=item,
                        numero=numero,
                        defaults={'montada': True, 'separada': False}
                    )

    # Se todos os itens são insumos, pula direto para picking
    todos_insumos = all(
        item.produto.categoria == 'insumo'
        for item in pedido.itens.select_related('produto').all()
    )
    if todos_insumos and pedido.itens.exists():
        pedido.status = pedido.Status.PICKING
        pedido.save(update_fields=['status', 'atualizado_em'])


class Pedido(models.Model):

    class Status(models.TextChoices):
        OPEN            = "open",            "Em aberto"
        AGUARD_PRODUCAO = "aguard_producao", "Aguardando Produção"
        CUTTING         = "cutting",         "Em Corte"
        ASSEMBLING      = "assembling",      "Em Montagem"
        PICKING         = "picking",         "Em Separação"
        SHIPPED         = "shipped",         "Enviado"
        DELIVERED       = "delivered",       "Entregue"
        CANCELED        = "canceled",        "Cancelado"
        DEVOLVIDO = "devolvido", "Devolução"

    class TipoVenda(models.TextChoices):
        DIRECT      = "direct",      "Venda direta"
        REPLACEMENT = "replacement", "Reposição"
        EXCHANGE    = "exchange",    "Troca"
        MAINTENANCE = "maintenance", "Manutenção"
        ADVERTISING = "advertising", "Publicidade"
        COMODATO    = "comodato",    "Comodato"

    class PrazoConfeccao(models.TextChoices):
        DIAS_15        = "15",     "15 dias"
        DIAS_20        = "20",     "20 dias"
        DIAS_25        = "25",     "25 dias"
        DIAS_30        = "30",     "30 dias"
        PRONTA_ENTREGA = "pronta", "À Pronta Entrega"

    numero             = models.CharField(max_length=10, unique=True, blank=True, verbose_name='Número do Pedido', db_index=True)
    cliente            = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pedidos', verbose_name='Cliente')
    criado_por         = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pedidos_criados', verbose_name='Criado por')
    responsavel        = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pedidos_responsavel', null=True, blank=True, verbose_name='Responsável')
    status             = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True, verbose_name='Status')
    urgente            = models.BooleanField(default=False, verbose_name='Urgente')
    tipo_venda         = models.CharField(max_length=20, choices=TipoVenda.choices, blank=True, verbose_name='Tipo de Venda')
    pedido_cliente     = models.CharField(max_length=100, blank=True, verbose_name='Pedido do Cliente')
    condicao_pagamento = models.CharField(max_length=100, blank=True, verbose_name='Condição de Pagamento')
    contato            = models.CharField(max_length=100, blank=True, verbose_name='Contato')
    transportadora     = models.CharField(max_length=50, blank=True, verbose_name='Transportadora')
    local_saida        = models.ForeignKey(
        'core.Local', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pedidos_saida',
        verbose_name='Local de Saída'
    )
    frete              = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Frete')
    prazo_confeccao = models.CharField(
    max_length=10, choices=PrazoConfeccao.choices, blank=True,
    verbose_name='Prazo de Confecção'
)
    data_entrega       = models.DateField(null=True, blank=True, verbose_name='Data de Entrega')
    observacoes        = models.TextField(blank=True, verbose_name='Observações')
    observacoes_internas = models.TextField(blank=True, verbose_name='Observações Internas')
    total_produtos     = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Produtos')
    total_desconto     = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Desconto')
    total_impostos     = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Impostos')
    total_geral        = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total Geral')
    criado_em          = models.DateTimeField(auto_now_add=True)
    atualizado_em      = models.DateTimeField(auto_now=True)
    cancelado_por      = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pedidos_cancelados',
        verbose_name='Cancelado por'
    )
    motivo_cancelamento = models.TextField(blank=True, verbose_name='Motivo do Cancelamento')
    cancelado_em        = models.DateTimeField(null=True, blank=True, verbose_name='Cancelado em')
    registrado_devolucao_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pedidos_devolvidos',
        verbose_name='Devolução registrada por'
    )
    motivo_devolucao = models.TextField(blank=True, verbose_name='Motivo da Devolução')
    devolvido_em     = models.DateTimeField(null=True, blank=True, verbose_name='Devolvido em')
    operador_corte      = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pedidos_corte',
        verbose_name='Operador de Corte'
    )
    token_expedicao  = models.CharField(
        max_length=64, unique=True, blank=True,
        verbose_name='Token de Expedição'
    )
    token_separacao  = models.CharField(
        max_length=64, unique=True, blank=True,
        verbose_name='Token de Separação'
    )
    separado         = models.BooleanField(default=False, verbose_name='Separado')

    

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
        if not self.token_expedicao:
            self.token_expedicao = secrets.token_urlsafe(32)
        if not self.token_separacao:
            self.token_separacao = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

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
    def progresso_corte(self):
        from producao_corte.models import ProdutoCortado
        resultado = []
        for item in self.itens.select_related('produto').all():
            if item.produto.categoria == 'insumo':
                continue
            cortado = ProdutoCortado.objects.filter(
                pedido=self,
                produto=item.produto,
            ).count()
            resultado.append({
                'nome':     item.produto.nome,
                'cortado':  cortado,
                'total':    item.quantidade,
                'completo': cortado >= item.quantidade,
                'falta':    max(0, item.quantidade - cortado),
            })
        return resultado

    @property
    def corte_completo(self):
        return all(p['completo'] for p in self.progresso_corte)

    @property
    def progresso_montagem(self):
        from producao_corte.models import ProdutoCortado
        resultado = []
        for item in self.itens.select_related('produto').all():
            if item.produto.categoria == 'insumo':
                continue
            total   = ProdutoCortado.objects.filter(pedido=self, produto=item.produto).count()
            montado = ProdutoCortado.objects.filter(
                pedido=self, produto=item.produto, montada_em__isnull=False,
            ).count()
            resultado.append({
                'nome':     item.produto.nome,
                'montado':  montado,
                'total':    total if total > 0 else item.quantidade,
                'completo': total > 0 and montado >= total,
                'falta':    max(0, (total if total > 0 else item.quantidade) - montado),
            })
        return resultado

    @property
    def montagem_completa(self):
        return all(p['completo'] for p in self.progresso_montagem)

    @property
    def status_separacao(self):
        from vendas.models.unidade_pedido import UnidadePedido
        from producao_corte.models import ProdutoCortado

        total     = 0
        separadas = 0

        # Itens do tipo insumo — rastreados via UnidadePedido
        total     += UnidadePedido.objects.filter(item__pedido=self).count()
        separadas += UnidadePedido.objects.filter(item__pedido=self, separada=True).count()

        # Itens de produto final (cortados/montados) — rastreados via ProdutoCortado
        total     += ProdutoCortado.objects.filter(pedido=self).count()
        separadas += ProdutoCortado.objects.filter(
            pedido=self, status__in=['separado', 'enviado']
        ).count()

        return {
            'total':         total,
            'separadas':     separadas,
            'tudo_separado': separadas >= total,
        }

    def sync_status(self):
        protected = {
            self.Status.CUTTING,
            self.Status.ASSEMBLING,
            self.Status.PICKING,
            self.Status.SHIPPED,
            self.Status.DELIVERED,
            self.Status.CANCELED,
            self.Status.DEVOLVIDO,
        }
        if self.status in protected:
            return

        if self.is_free_sale:
            new_status = self.Status.AGUARD_PRODUCAO
        else:
            if self.pagamentos.exists():
                new_status = self.Status.AGUARD_PRODUCAO
            else:
                new_status = self.Status.OPEN

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status', 'atualizado_em'])
            if new_status == self.Status.AGUARD_PRODUCAO:
                _criar_unidades_insumos(self)

class ItemPedido(models.Model):
    pedido         = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens', verbose_name='Pedido')
    produto        = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_pedido', verbose_name='Produto')
    quantidade     = models.PositiveIntegerField(default=1, verbose_name='Quantidade')
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço Unitário')

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
        total  = sum(
            (i.preco_unitario * i.quantidade).quantize(TWO)
            for i in pedido.itens.all()
        )
        pedido.total_produtos = total
        pedido.total_geral    = (
            total - pedido.total_desconto + pedido.total_impostos + pedido.frete
        ).quantize(TWO)
        pedido.save(update_fields=['total_produtos', 'total_geral', 'atualizado_em'])