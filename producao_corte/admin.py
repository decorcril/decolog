from django.contrib import admin
from producao_corte.models import RegistroCorte, ItemCorte, ProdutoCortado


class ItemCorteInline(admin.TabularInline):
    model = ItemCorte
    extra = 0
    fields = ['chapa', 'quantidade_chapa']


class ProdutoCortadoInline(admin.TabularInline):
    model = ProdutoCortado
    extra = 0
    fields = ['produto', 'status', 'pedido', 'token']
    readonly_fields = ['token']


@admin.register(RegistroCorte)
class RegistroCorteAdmin(admin.ModelAdmin):
    list_display   = ['id', 'data', 'operador', 'pedido', 'criado_em']
    list_filter    = ['data', 'operador']
    search_fields  = ['pedido__numero', 'observacao']
    readonly_fields = ['criado_em']
    inlines        = [ItemCorteInline]


@admin.register(ProdutoCortado)
class ProdutoCortadoAdmin(admin.ModelAdmin):
    list_display    = [
        'id', 'produto', 'status', 'pedido', 'token_curto',
        'cortada_por', 'montada_em', 'separada_em',
    ]
    list_filter     = ['status', 'produto__categoria', 'montada_em']
    search_fields   = ['token', 'produto__nome', 'pedido__numero']
    readonly_fields = [
        'token', 'montada_em', 'separada_em',
        'desmembrada_em', 'origem_desmembramento',
    ]
    autocomplete_fields = ['produto', 'pedido']

    @admin.display(description='Token')
    def token_curto(self, obj):
        return obj.token[:8] if obj.token else '—'