from django.contrib import admin
from django.urls import path, include

from core.views.auth import logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/logout/', logout_view, name='logout'),
    path('', include('core.urls')),
    path('produtos/', include('produtos.urls')),
    path('estoque/', include('estoque.urls')),
    path('movimentacoes/', include('movimentacoes.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('producao/', include('producao_corte.urls')),
]