from django.urls import path
from core.views import (
    dashboard,
    local_list, local_create, local_update, local_delete,
    fornecedor_list, fornecedor_create, fornecedor_update, fornecedor_delete,
)

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
]