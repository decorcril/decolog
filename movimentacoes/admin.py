from django.contrib import admin
from movimentacoes.models import Movimentacao

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ['data_hora', 'produto', 'tipo', 'motivo', 'quantidade', 'local', 'usuario']
    list_filter = ['tipo', 'motivo']
    search_fields = ['produto__nome', 'produto__codigo']
    ordering = ['-data_hora']