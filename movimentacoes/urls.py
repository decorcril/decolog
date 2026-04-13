from django.urls import path
from movimentacoes.views import (
    entrada_create,
    transferencia_create,
    saida_create,
    historico_list,
)

app_name = 'movimentacoes'

urlpatterns = [
    path('entrada/', entrada_create, name='entrada'),
    path('transferencia/', transferencia_create, name='transferencia'),
    path('saida/', saida_create, name='saida'),
    path('historico/', historico_list, name='historico'),
]