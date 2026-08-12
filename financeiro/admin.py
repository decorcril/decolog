# financeiro/admin.py
from django.contrib import admin
from financeiro.models import ContaPagar, ContaPagarParcela, PagamentoContaPagar


class PagamentoInline(admin.TabularInline):
    model = PagamentoContaPagar
    extra = 0
    readonly_fields = ['criado_em']


class ParcelaInline(admin.TabularInline):
    model = ContaPagarParcela
    extra = 0
    readonly_fields = ['status']
    fields = ['numero', 'vencimento', 'valor', 'status']


@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'fornecedor', 'valor_total', 'data_emissao', 'categoria', 'status_display']
    list_filter = ['categoria', 'fornecedor']
    search_fields = ['descricao', 'numero_documento', 'fornecedor__nome']
    inlines = [ParcelaInline]

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = 'Status'


@admin.register(ContaPagarParcela)
class ContaPagarParcelaAdmin(admin.ModelAdmin):
    list_display = ['conta', 'numero', 'vencimento', 'valor', 'status']
    list_filter = ['status']
    search_fields = ['conta__descricao', 'conta__fornecedor__nome']
    inlines = [PagamentoInline]