from django.urls import path
from .views import registro_corte_create, registro_corte_list

app_name = 'producao_corte'

urlpatterns = [
    path('', registro_corte_list, name='list'),
    path('novo/', registro_corte_create, name='create'),
]