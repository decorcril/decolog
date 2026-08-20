from functools import reduce
import operator

from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from core.models import Local
from core.mixins import loja_do_usuario
from produtos.models import Produto
from estoque.models import Estoque


@login_required
def estoque_list(request):
    q = request.GET.get('q', '')
    local_id = request.GET.get('local', '')
    categoria = request.GET.get('categoria', '')

    loja_restrita = loja_do_usuario(request.user)

    # Se o usuário está restrito a uma loja, ignora qualquer local_id vindo
    # da URL e força o filtro pra loja dele — evita bypass via ?local=999.
    if loja_restrita:
        local_id = str(loja_restrita.pk)

    produtos = Produto.objects.filter(ativo=True)

    if q:
        termos = q.split()
        queries = [Q(nome__icontains=t) | Q(codigo__icontains=t) for t in termos]
        produtos = produtos.filter(reduce(operator.and_, queries))

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

    # Dropdown de locais: se restrito, mostra só a loja dele (sem opção de trocar).
    locais = Local.objects.filter(pk=loja_restrita.pk) if loja_restrita else Local.objects.filter(ativo=True)

    return render(request, 'estoque/consulta/list.html', {
        'produtos': page_obj,
        'page_obj': page_obj,
        'locais': locais,
        'loja_restrita': loja_restrita,
        'q': q,
        'local_id': local_id,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    })


@login_required
def saldo_por_produto(request, produto_id):
    loja_restrita = loja_do_usuario(request.user)

    estoques = Estoque.objects.filter(
        produto_id=produto_id,
        quantidade__gt=0
    ).select_related('local')

    if loja_restrita:
        estoques = estoques.filter(local=loja_restrita)

    dados = [
        {
            'local': e.local.nome,
            'local_id': e.local.id,
            'quantidade': int(e.quantidade) if e.quantidade == e.quantidade.to_integral_value() else str(e.quantidade),
        }
        for e in estoques
    ]
    return JsonResponse({'saldos': dados})