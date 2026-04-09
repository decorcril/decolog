from django.urls import path
from estoque.views import estoque_list

app_name = 'estoque'

urlpatterns = [
    path('', estoque_list, name='lista'),
]