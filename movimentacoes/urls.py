from django.urls import path
from movimentacoes.views import entrada_create, transferencia_create

app_name = 'movimentacoes'

urlpatterns = [
    path('entrada/', entrada_create, name='entrada'),
    path('transferencia/', transferencia_create, name='transferencia'),
]