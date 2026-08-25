from django.urls import path
from .views import (
    registro_corte_create,
    registro_corte_list,
    registro_corte_delete,
    registro_corte_detail,
    etiquetas_registro_corte,
    desmembrar_kit,
    confirmar_montagem_lote,
)

app_name = 'producao_corte'

urlpatterns = [
    path('',                                    registro_corte_list,       name='list'),
    path('novo/',                               registro_corte_create,     name='create'),
    path('<int:pk>/',                           registro_corte_detail,     name='detail'),
    path('<int:pk>/excluir/',                   registro_corte_delete,     name='delete'),
    path('<int:pk>/etiquetas/',                 etiquetas_registro_corte,  name='etiquetas'),
    path('<int:pk>/confirmar-montagem-lote/',   confirmar_montagem_lote,   name='confirmar_montagem_lote'),
    path('peca/<str:token>/desmembrar/',        desmembrar_kit,            name='desmembrar_kit'),
]