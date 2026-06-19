from django.urls import path
from vendas import views

app_name = 'vendas'

urlpatterns = [
    path('', views.pedido_list, name='pedido_list'),
    path('novo/', views.pedido_create, name='pedido_create'),
    path('<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('<int:pk>/editar/', views.pedido_edit, name='pedido_edit'),
    path('<int:pk>/status/', views.pedido_status, name='pedido_status'),
    path('<int:pk>/itens/<int:item_pk>/remover/', views.item_remove, name='item_remove'),
    path('<int:pk>/pagamentos/adicionar/', views.pagamento_add, name='pagamento_add'),
    path('<int:pk>/pagamentos/<int:pag_pk>/apagar/', views.pagamento_delete, name='pagamento_delete'),
    path('autocomplete/clientes/', views.autocomplete_cliente, name='autocomplete_cliente'),
    path('autocomplete/produtos/', views.autocomplete_produto, name='autocomplete_produto'),
    path('<int:pk>/itens/<int:item_pk>/atualizar/', views.item_update, name='item_update'),
    path('frete/calcular/', views.calcular_frete_view, name='calcular_frete'),
    path('orcamentos/',                          views.orcamento_list,     name='orcamento_list'),
    path('orcamentos/novo/',                     views.orcamento_create,   name='orcamento_create'),
    path('orcamentos/<int:pk>/',                 views.orcamento_detail,   name='orcamento_detail'),
    path('orcamentos/<int:pk>/aprovar/',         views.orcamento_aprovar,  name='orcamento_aprovar'),
    path('orcamentos/<int:pk>/rejeitar/',        views.orcamento_rejeitar, name='orcamento_rejeitar'),
    path('<int:pk>/itens/adicionar/', views.item_add, name='item_add'),
    path('laser/',                        views.laser_list,       name='laser_list'),
    path('laser/<int:pk>/confirmar/',     views.laser_confirmar,  name='laser_confirmar'),
    path('laser/<int:pk>/finalizar/',     views.laser_finalizar,  name='laser_finalizar'),
    path('montagem/',                     views.montagem_list,    name='montagem_list'),
    path('montagem/<int:pk>/finalizar/',  views.montagem_finalizar, name='montagem_finalizar'),
]