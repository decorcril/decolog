from django.urls import path
from estoque.views import estoque_list, saldo_por_produto

app_name = 'estoque'

urlpatterns = [
    path('', estoque_list, name='lista'),
    path('saldo/<int:produto_id>/', saldo_por_produto, name='saldo_produto'),
]