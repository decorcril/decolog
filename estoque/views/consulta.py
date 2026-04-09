from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from estoque.models import Estoque
from core.models import Local
from produtos.models import Produto


@login_required
def estoque_list(request):
    q = request.GET.get('q', '')
    local_id = request.GET.get('local', '')
    categoria = request.GET.get('categoria', '')

    estoques = Estoque.objects.select_related(
        'produto', 'local'
    ).filter(quantidade__gt=0)

    if q:
        estoques = estoques.filter(produto__nome__icontains=q)
    if local_id:
        estoques = estoques.filter(local__id=local_id)
    if categoria:
        estoques = estoques.filter(produto__categoria=categoria)

    locais = Local.objects.filter(ativo=True)

    return render(request, 'estoque/consulta/list.html', {
        'estoques': estoques,
        'locais': locais,
        'q': q,
        'local_id': local_id,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    })