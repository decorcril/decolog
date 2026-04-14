from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core import models
from estoque.models import Estoque
from core.models import Local
from produtos.models import Produto
from django.db.models import F


@login_required
def estoque_baixo(request):
    local_id = request.GET.get('local', '')
    categoria = request.GET.get('categoria', '')

    estoques = Estoque.objects.select_related(
    'produto', 'local'
    ).filter(
        estoque_minimo__gt=0,
        quantidade__lte=F('estoque_minimo') * 2
    ).order_by('local__nome', 'produto__nome')

    if local_id:
        estoques = estoques.filter(local__id=local_id)
    if categoria:
        estoques = estoques.filter(produto__categoria=categoria)

    return render(request, 'relatorios/estoque_baixo.html', {
        'estoques': estoques,
        'locais': Local.objects.filter(ativo=True),
        'local_id': local_id,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
        'total': estoques.count(),
    })