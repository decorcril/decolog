from django.urls import path
from .views import registro_corte_create, registro_corte_list, registro_corte_delete

app_name = 'producao_corte'

urlpatterns = [
    path('', registro_corte_list, name='list'),
    path('novo/', registro_corte_create, name='create'),
    path('<int:pk>/excluir/', registro_corte_delete, name='delete'),
]