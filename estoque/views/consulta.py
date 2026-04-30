from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from core.models import Local
from produtos.models import Produto
from estoque.models import Estoque


@login_required
def estoque_list(request):
    q = request.GET.get('q', '')
    local_id = request.GET.get('local', '')
    categoria = request.GET.get('categoria', '')

    produtos = Produto.objects.filter(ativo=True)

    if q:
        produtos = produtos.filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    resultado = []
    for produto in produtos:
        saldos = Estoque.objects.filter(
            produto=produto, quantidade__gt=0
        ).select_related('local')

        if local_id:
            saldos = saldos.filter(local__id=local_id)

        if saldos.exists():
            produto.saldos_por_local = saldos
            resultado.append(produto)

    paginator = Paginator(resultado, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'estoque/consulta/list.html', {
        'produtos': page_obj,
        'page_obj': page_obj,
        'locais': Local.objects.filter(ativo=True),
        'q': q,
        'local_id': local_id,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    })


@login_required
def saldo_por_produto(request, produto_id):
    estoques = Estoque.objects.filter(
        produto_id=produto_id,
        quantidade__gt=0
    ).select_related('local')

    dados = [
        {
            'local': e.local.nome,
            'local_id': e.local.id,
            'quantidade': int(e.quantidade) if e.quantidade == e.quantidade.to_integral_value() else str(e.quantidade),
        }
        for e in estoques
    ]
    return JsonResponse({'saldos': dados})