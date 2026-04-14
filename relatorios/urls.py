from django.urls import path
from relatorios.views import estoque_atual, estoque_baixo

app_name = 'relatorios'

urlpatterns = [
    path('estoque-atual/', estoque_atual, name='estoque_atual'),
    path('estoque-baixo/', estoque_baixo, name='estoque_baixo'),
]