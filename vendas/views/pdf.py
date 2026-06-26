from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from core.mixins import acesso_vendas
from vendas.models import Pedido


@acesso_vendas
def pedido_pdf(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return HttpResponse(f'PDF do pedido {pedido.numero} — em breve', content_type='text/plain')