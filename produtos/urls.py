from django.urls import path
from produtos.views import produto_list, produto_create, produto_update, produto_delete

app_name = 'produtos'

urlpatterns = [
    path('', produto_list, name='lista'),
    path('novo/', produto_create, name='criar'),
    path('<int:pk>/editar/', produto_update, name='editar'),
    path('<int:pk>/excluir/', produto_delete, name='excluir'),
]