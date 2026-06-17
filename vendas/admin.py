from django.contrib import admin
from vendas.models import Pedido, ItemPedido, Pagamento, Envio


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ['produto', 'quantidade', 'preco_unitario', 'subtotal']
    readonly_fields = ['subtotal']


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    fields = ['metodo', 'valor', 'transacao', 'pago_em', 'criado_por']
    readonly_fields = ['pago_em']


class EnvioInline(admin.StackedInline):
    model = Envio
    extra = 0
    fields = ['rastreio', 'transportadora', 'arquivo', 'criado_por']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'status', 'tipo_venda', 'total_geral', 'criado_por', 'criado_em']
    list_filter  = ['status', 'tipo_venda']
    search_fields = ['numero', 'cliente__nome']
    readonly_fields = ['numero', 'total_produtos', 'total_geral', 'criado_em', 'atualizado_em']
    inlines = [ItemPedidoInline, PagamentoInline, EnvioInline]


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display  = ['pedido', 'metodo', 'valor', 'transacao', 'pago_em', 'criado_por']
    list_filter   = ['metodo']
    search_fields = ['transacao', 'pedido__numero']
    readonly_fields = ['pago_em']