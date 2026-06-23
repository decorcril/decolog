from django.urls import path
from clientes import views as clientes_views
from core.views import (
    dashboard,
    dashboard_vendas,
    local_list, local_create, local_update, local_delete,
    fornecedor_list, fornecedor_create, fornecedor_update, fornecedor_delete,
)
from core.views.fornecedor import tag_delete, tag_list
from core.views.notificacao import notificacoes_lista, notificacoes_marcar_lida

app_name = 'core'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    # Locais
    path('locais/', local_list, name='local_list'),
    path('locais/novo/', local_create, name='local_create'),
    path('locais/<int:pk>/editar/', local_update, name='local_update'),
    path('locais/<int:pk>/excluir/', local_delete, name='local_delete'),
    # Fornecedores
    path('fornecedores/', fornecedor_list, name='fornecedor_list'),
    path('fornecedores/novo/', fornecedor_create, name='fornecedor_create'),
    path('fornecedores/<int:pk>/editar/', fornecedor_update, name='fornecedor_update'),
    path('fornecedores/<int:pk>/excluir/', fornecedor_delete, name='fornecedor_delete'),
    path('fornecedores/tags/', tag_list, name='tag_list'),
    path('fornecedores/tags/<int:pk>/excluir/', tag_delete, name='tag_delete'),
    # Notificações
    path('notificacoes/', notificacoes_lista, name='notificacoes_lista'),
    path('notificacoes/<int:pedido_pk>/lida/', notificacoes_marcar_lida, name='notificacoes_marcar_lida'),
    path('dashboard/vendas/', dashboard_vendas, name='dashboard_vendas'),
]