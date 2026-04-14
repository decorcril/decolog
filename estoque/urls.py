from django.urls import path
from estoque.views import estoque_list, saldo_por_produto, estoque_minimo_edit, estoque_detalhe

app_name = 'estoque'

urlpatterns = [
    path('', estoque_list, name='lista'),
    path('saldo/<int:produto_id>/', saldo_por_produto, name='saldo_produto'),
    path('minimo/<int:pk>/', estoque_minimo_edit, name='editar_minimo'),
    path('produto/<int:produto_id>/', estoque_detalhe, name='detalhe'),
]