from django.urls import path
from .views import registrar_producao, producao_list

app_name = 'montagem'

urlpatterns = [
    path('', producao_list, name='list'),
    path('registrar/', registrar_producao, name='registrar'),
]