from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
    path('produtos/', include('produtos.urls')),
    path('estoque/', include('estoque.urls')),
    path('movimentacoes/', include('movimentacoes.urls')),
    path('relatorios/', include('relatorios.urls')),
]