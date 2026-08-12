# financeiro/urls.py
from django.urls import path
from financeiro.views import contas_pagar

app_name = 'financeiro'

urlpatterns = [
    path('contas-pagar/', contas_pagar.conta_pagar_list, name='contas_pagar_list'),
    path('contas-pagar/nova/', contas_pagar.conta_pagar_create, name='contas_pagar_create'),
    path('contas-pagar/<int:pk>/', contas_pagar.conta_pagar_detail, name='contas_pagar_detail'),
    path('contas-pagar/<int:pk>/editar/', contas_pagar.conta_pagar_edit, name='contas_pagar_edit'),
    path('contas-pagar/<int:pk>/excluir/', contas_pagar.conta_pagar_delete, name='contas_pagar_delete'),
    path('contas-pagar/<int:pk>/cancelar/', contas_pagar.conta_pagar_cancelar, name='contas_pagar_cancelar'),
    path('contas-pagar/<int:conta_pk>/parcela/<int:parcela_pk>/pagamento/',
         contas_pagar.pagamento_parcela_add, name='pagamento_parcela_add'),
    path('contas-pagar/<int:conta_pk>/parcela/<int:parcela_pk>/pagamento/<int:pag_pk>/excluir/',
         contas_pagar.pagamento_parcela_delete, name='pagamento_parcela_delete'),
]