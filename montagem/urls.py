from django.urls import path
from .views import registrar_producao, producao_list, producao_detail

app_name = 'montagem'

urlpatterns = [
    path('', producao_list, name='list'),
    path('registrar/', registrar_producao, name='registrar'),
    path('<int:pk>/', producao_detail, name='detail'),
]