from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from core.mixins import estoque_ou_gerente
from estoque.models import Estoque
from core.models import Local
from produtos.models import Produto


@estoque_ou_gerente
def estoque_atual(request):
    q = request.GET.get('q', '')
    local_id = request.GET.get('local', '')
    categoria = request.GET.get('categoria', '')

    estoques = Estoque.objects.select_related(
        'produto', 'local'
    ).filter(quantidade__gt=0).order_by('local__nome', 'produto__nome')

    if q:
        estoques = estoques.filter(
            Q(produto__nome__icontains=q) | Q(produto__codigo__icontains=q)
        )
    if local_id:
        estoques = estoques.filter(local__id=local_id)
    if categoria:
        estoques = estoques.filter(produto__categoria=categoria)

    # Agrupa por local
    locais_dict = {}
    for e in estoques:
        nome_local = e.local.nome
        if nome_local not in locais_dict:
            locais_dict[nome_local] = []
        locais_dict[nome_local].append(e)

    # Pagina por local
    locais_lista = list(locais_dict.items())
    paginator = Paginator(locais_lista, 3)  # 3 locais por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'relatorios/estoque_atual.html', {
        'locais_page': page_obj,
        'page_obj': page_obj,
        'locais': Local.objects.filter(ativo=True),
        'q': q,
        'local_id': local_id,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
        'total_itens': estoques.count(),
    })