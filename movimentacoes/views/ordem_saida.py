from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from movimentacoes.models import OrdemSaida, ItemOrdemSaida
from produtos.models import Produto
from estoque.models import Estoque
from core.mixins import estoquista_ou_admin


@estoquista_ou_admin
def ordem_saida_criar(request):
    from core.models import Local

    locais = Local.objects.filter(ativo=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True).order_by('nome')
    motivo_choices = OrdemSaida.MOTIVO_CHOICES

    if request.method == 'POST':
        local_id = request.POST.get('local_origem')
        motivo = request.POST.get('motivo')
        observacao = request.POST.get('observacao', '')
        produto_ids = request.POST.getlist('produto_id')
        quantidades = request.POST.getlist('quantidade')

        if not local_id:
            messages.error(request, 'Selecione o local de origem.')
            return render(request, 'movimentacoes/ordem_saida/form.html', {
                'locais': locais, 'produtos': produtos, 'motivo_choices': motivo_choices,
            })

        if not produto_ids:
            messages.error(request, 'Adicione pelo menos um produto.')
            return render(request, 'movimentacoes/ordem_saida/form.html', {
                'locais': locais, 'produtos': produtos, 'motivo_choices': motivo_choices,
            })

        try:
            with transaction.atomic():
                local_origem = Local.objects.get(pk=local_id)

                ordem = OrdemSaida.objects.create(
                    numero=OrdemSaida.gerar_numero(),
                    local_origem=local_origem,
                    motivo=motivo,
                    observacao=observacao,
                    criado_por=request.user,
                )

                for pid, qtd in zip(produto_ids, quantidades):
                    if not pid or not qtd:
                        continue

                    produto = Produto.objects.get(pk=pid)
                    quantidade = Decimal(str(qtd))

                    if quantidade <= 0:
                        continue

                    saldo = Estoque.get_or_create_saldo(produto, local_origem)
                    saldo.subtrair(quantidade)

                    # Registra movimentação
                    from movimentacoes.models import Movimentacao
                    Movimentacao.objects.create(
                        produto=produto,
                        local=local_origem,
                        tipo='saida',
                        motivo=motivo,
                        quantidade=quantidade,
                        observacao=observacao,
                        usuario=request.user,
                    )

                    ItemOrdemSaida.objects.create(
                        ordem=ordem,
                        produto=produto,
                        quantidade=quantidade,
                    )

            messages.success(request, f'Saída {ordem.numero} registrada com sucesso!')
            return redirect('movimentacoes:ordem_saida_detalhe', pk=ordem.pk)

        except ValidationError as e:
            messages.error(request, f'Estoque insuficiente: {e.messages[0]}')
        except Exception as e:
            messages.error(request, f'Erro ao registrar saída: {e}')

    return render(request, 'movimentacoes/ordem_saida/form.html', {
        'locais': locais,
        'produtos': produtos,
        'motivo_choices': motivo_choices,
    })


@estoquista_ou_admin
def ordem_saida_list(request):
    motivo = request.GET.get('motivo', '')
    ordens = OrdemSaida.objects.select_related('local_origem', 'criado_por')
    if motivo:
        ordens = ordens.filter(motivo=motivo)

    return render(request, 'movimentacoes/ordem_saida/list.html', {
        'ordens': ordens,
        'motivo': motivo,
        'motivo_choices': OrdemSaida.MOTIVO_CHOICES,
    })


@estoquista_ou_admin
def ordem_saida_detalhe(request, pk):
    ordem = get_object_or_404(OrdemSaida, pk=pk)
    itens = ordem.itens.select_related('produto')
    return render(request, 'movimentacoes/ordem_saida/detalhe.html', {
        'ordem': ordem,
        'itens': itens,
    })