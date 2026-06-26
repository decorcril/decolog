from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from decimal import Decimal
from functools import reduce
import operator

from core.mixins import montagem_ou_gerente
from movimentacoes.models import Movimentacao
from produtos.models import Produto
from core.models import Local
from montagem.models import RegistroMontagem, ItemMontagem


@montagem_ou_gerente
def registrar_producao(request):
    from vendas.models import Pedido

    pedido_pk = request.GET.get('pedido_pk') or request.POST.get('pedido_pk')
    pedido    = None
    if pedido_pk:
        pedido = get_object_or_404(Pedido, pk=pedido_pk)

    produtos_finais = Produto.objects.filter(
        categoria='produto_final', ativo=True
    ).order_by('nome')

    fabrica = Local.objects.filter(tipo='fabrica').first()

    if request.method == 'POST':
        observacao = request.POST.get('observacao', '')

        if pedido:
            try:
                registro = RegistroMontagem.objects.create(
                    pedido=pedido,
                    operador=request.user,
                    observacao=observacao,
                )

                for item in pedido.itens.select_related('produto').all():
                    qty_str = request.POST.get(f'quantidade_{item.produto.nome}', '0')
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        qty = 0

                    if qty <= 0:
                        continue

                    # Não permite montar mais do que o total do pedido
                    ja_montado = ItemMontagem.objects.filter(
                        registro__pedido=pedido,
                        produto=item.produto,
                    ).exclude(registro=registro).aggregate(
                        total=Sum('quantidade')
                    )['total'] or 0

                    qty = min(qty, item.quantidade - ja_montado)
                    if qty <= 0:
                        continue

                    ItemMontagem.objects.create(
                        registro=registro,
                        produto=item.produto,
                        quantidade=qty,
                    )
                    Movimentacao.objects.create(
                        produto=item.produto,
                        local=fabrica,
                        tipo='entrada',
                        motivo='producao',
                        quantidade=qty,
                        observacao=f'Montagem — Pedido {pedido.numero}',
                        usuario=request.user,
                    )

                # Verifica progresso
                pedido.refresh_from_db()
                progresso       = pedido.progresso_montagem
                todos_completos = all(p['completo'] for p in progresso)
                incompletos     = [p for p in progresso if not p['completo']]

                if todos_completos:
                    pedido.status = Pedido.Status.PICKING
                    pedido.save(update_fields=['status', 'atualizado_em'])
                    messages.success(request, f'Montagem completa! Pedido {pedido.numero} enviado para separação.')
                else:
                    pedido.status = Pedido.Status.ASSEMBLING
                    pedido.save(update_fields=['status', 'atualizado_em'])
                    faltam = ', '.join(
                        f"{p['nome']} ({p['falta']} restante{'s' if p['falta'] > 1 else ''})"
                        for p in incompletos
                    )
                    messages.warning(request, f'Montagem parcial registrada. Faltam: {faltam}')

                return redirect('vendas:montagem_list')

            except Exception as e:
                messages.error(request, f'Erro ao registrar: {e}')

        else:
            # Registro avulso
            produto_id = request.POST.get('produto')
            quantidade = request.POST.get('quantidade')

            if not produto_id:
                messages.error(request, 'Selecione um produto.')
            elif not quantidade:
                messages.error(request, 'Informe a quantidade.')
            else:
                try:
                    produto  = Produto.objects.get(pk=produto_id)
                    registro = RegistroMontagem.objects.create(
                        operador=request.user,
                        observacao=observacao,
                    )
                    ItemMontagem.objects.create(
                        registro=registro,
                        produto=produto,
                        quantidade=Decimal(quantidade),
                    )
                    Movimentacao.objects.create(
                        produto=produto,
                        local=fabrica,
                        tipo='entrada',
                        motivo='producao',
                        quantidade=Decimal(quantidade),
                        observacao=observacao,
                        usuario=request.user,
                    )
                    messages.success(request, f'Produção de {produto.nome} registrada!')
                    return redirect('montagem:registrar')
                except Exception as e:
                    messages.error(request, f'Erro ao registrar: {e}')

    # Pré-preenche produtos do pedido para o template
    produtos_pedido = []
    if pedido:
        produtos_pedido = [
            {
                'nome':       item.produto.nome,
                'quantidade': item.quantidade,
            }
            for item in pedido.itens.select_related('produto').all()
        ]

    return render(request, 'montagem/form.html', {
        'produtos_finais': produtos_finais,
        'fabrica':         fabrica,
        'pedido':          pedido,
        'pedido_pk':       pedido_pk or '',
        'produtos_pedido': produtos_pedido,
    })

@montagem_ou_gerente
def montagem_list(request):
    from vendas.models import Pedido

    pedidos = Pedido.objects.filter(
        status=Pedido.Status.ASSEMBLING
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    pedidos_com_progresso = []
    for pedido in pedidos:
        pedidos_com_progresso.append({
            'pedido':    pedido,
            'progresso': pedido.progresso_montagem,
        })

    return render(request, 'vendas/montagem_list.html', {
        'pedidos': pedidos_com_progresso,
    })


@montagem_ou_gerente
def montagem_finalizar(request, pk):
    from vendas.models import Pedido
    from django.urls import reverse

    pedido = get_object_or_404(Pedido, pk=pk, status=Pedido.Status.ASSEMBLING)

    if request.method == 'POST':
        url = reverse('montagem:registrar') + f'?pedido_pk={pedido.pk}'
        return redirect(url)

    return redirect('vendas:montagem_list')


@montagem_ou_gerente
def producao_list(request):
    q           = request.GET.get('q', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim    = request.GET.get('data_fim', '')

    movimentacoes = Movimentacao.objects.filter(
        motivo='producao'
    ).select_related('produto', 'local', 'usuario').order_by('-data_hora')

    if q:
        termos  = q.split()
        queries = [Q(produto__nome__icontains=t) | Q(produto__codigo__icontains=t) for t in termos]
        movimentacoes = movimentacoes.filter(reduce(operator.and_, queries))

    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)

    paginator   = Paginator(movimentacoes, 20)
    page_number = request.GET.get('page')
    page_obj    = paginator.get_page(page_number)

    return render(request, 'montagem/list.html', {
        'movimentacoes': page_obj,
        'page_obj':      page_obj,
        'q':             q,
        'data_inicio':   data_inicio,
        'data_fim':      data_fim,
    })


@montagem_ou_gerente
def producao_detail(request, pk):
    mov  = get_object_or_404(Movimentacao, pk=pk, motivo='producao')
    q    = request.GET.get('q', '')
    page = request.GET.get('page', '')

    return render(request, 'montagem/detail.html', {
        'mov':  mov,
        'q':    q,
        'page': page,
    })

@montagem_ou_gerente
def historico_montagem(request):
    registros = RegistroMontagem.objects.select_related(
        'operador', 'pedido__cliente'
    ).prefetch_related(
        'itens__produto'
    ).order_by('-criado_em')

    paginator = Paginator(registros, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'montagem/historico.html', {
        'registros': page_obj,
        'page_obj':  page_obj,
    })