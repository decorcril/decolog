from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
from functools import reduce
import operator
from core.mixins import montagem_ou_gerente
from movimentacoes.models import Movimentacao
from produtos.models import Produto
from core.models import Local


@montagem_ou_gerente
def registrar_producao(request):
    produtos_finais = Produto.objects.filter(
        categoria='produto_final', ativo=True
    ).order_by('nome')

    fabrica = Local.objects.filter(tipo='fabrica').first()

    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        quantidade = request.POST.get('quantidade')
        observacao = request.POST.get('observacao', '')

        if not produto_id:
            messages.error(request, 'Selecione um produto.')
        elif not quantidade:
            messages.error(request, 'Informe a quantidade.')
        else:
            try:
                produto = Produto.objects.get(pk=produto_id)
                Movimentacao.objects.create(
                    produto=produto,
                    local=fabrica,
                    tipo='entrada',
                    motivo='producao',
                    quantidade=Decimal(quantidade),
                    observacao=observacao,
                    usuario=request.user,
                )
                messages.success(request, f'Produção de {produto.nome} registrada com sucesso!')
                return redirect('montagem:registrar')
            except Exception as e:
                messages.error(request, f'Erro ao registrar: {e}')

    return render(request, 'montagem/form.html', {
        'produtos_finais': produtos_finais,
        'fabrica': fabrica,
    })


@montagem_ou_gerente
def producao_list(request):
    q = request.GET.get('q', '')

    movimentacoes = Movimentacao.objects.filter(
        motivo='producao'
    ).select_related('produto', 'local', 'usuario').order_by('-data_hora')

    if q:
        termos = q.split()
        queries = [Q(produto__nome__icontains=t) | Q(produto__codigo__icontains=t) for t in termos]
        movimentacoes = movimentacoes.filter(reduce(operator.and_, queries))

    paginator = Paginator(movimentacoes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'montagem/list.html', {
        'movimentacoes': page_obj,
        'page_obj': page_obj,
        'q': q,
    })


@montagem_ou_gerente
def producao_detail(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk, motivo='producao')
    q = request.GET.get('q', '')
    page = request.GET.get('page', '')

    return render(request, 'montagem/detail.html', {
        'mov': mov,
        'q': q,
        'page': page,
    })