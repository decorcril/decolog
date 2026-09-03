from django.contrib import admin
from estoque.models import Estoque


@admin.register(Estoque)
class EstoqueAdmin(admin.ModelAdmin):
    list_display  = [
        'produto', 'local', 'quantidade', 'estoque_minimo',
        'status_display', 'atualizado_em',
    ]
    list_filter   = ['local', 'produto__categoria']
    search_fields = ['produto__nome', 'produto__codigo', 'local__nome']
    readonly_fields = ['atualizado_em']
    autocomplete_fields = ['produto', 'local']

    @admin.display(description='Status')
    def status_display(self, obj):
        return obj.status_display or '—'