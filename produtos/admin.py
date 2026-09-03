from django.contrib import admin
from produtos.models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display  = ['codigo', 'nome', 'categoria', 'unidade_medida', 'ativo']
    list_filter   = ['categoria', 'ativo']
    search_fields = ['nome', 'codigo']