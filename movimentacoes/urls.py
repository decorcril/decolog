from django.urls import path
from movimentacoes.views import (
    entrada_create,
    transferencia_create,
    saida_create,
    historico_list,
    ajuste_create,
    ordem_criar,
    ordem_list,
    ordem_detalhe,
    ordem_confirmar,
    ordem_cancelar,
)
from movimentacoes.views.ordem_transferencia import ordem_imprimir
from movimentacoes.views.transferencia import transferencia_imprimir
from movimentacoes.views.ordem_saida import ordem_saida_criar, ordem_saida_list, ordem_saida_detalhe
app_name = 'movimentacoes'

urlpatterns = [
    path('entrada/', entrada_create, name='entrada'),
    path('transferencia/', transferencia_create, name='transferencia'),
    path('saida/', saida_create, name='saida'),
    path('historico/', historico_list, name='historico'),
    path('ajuste/', ajuste_create, name='ajuste'),
    path('ordem/nova/', ordem_criar, name='ordem_criar'),
    path('ordem/', ordem_list, name='ordem_list'),
    path('ordem/<int:pk>/', ordem_detalhe, name='ordem_detalhe'),
    path('ordem/<int:pk>/confirmar/', ordem_confirmar, name='ordem_confirmar'),
    path('ordem/<int:pk>/cancelar/', ordem_cancelar, name='ordem_cancelar'),
    path('ordem/<int:pk>/imprimir/', ordem_imprimir, name='ordem_imprimir'),
    path('transferencia/<int:pk>/imprimir/', transferencia_imprimir, name='transferencia_imprimir'),
    path('saida/lote/nova/', ordem_saida_criar, name='ordem_saida_criar'),
    path('saida/lote/', ordem_saida_list, name='ordem_saida_list'),
    path('saida/lote/<int:pk>/', ordem_saida_detalhe, name='ordem_saida_detalhe'),
]