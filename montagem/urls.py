from django.urls import path
from .views import registrar_producao, producao_list, producao_detail, historico_montagem, confirmar_montagem

app_name = 'montagem'

urlpatterns = [
    path('',                        producao_list,        name='list'),
    path('registrar/',              registrar_producao,   name='registrar'),
    path('historico/',              historico_montagem,   name='historico'),
    path('<int:pk>/',               producao_detail,      name='detail'),
    path('peca/<str:token>/',       confirmar_montagem,   name='confirmar_montagem'),
]