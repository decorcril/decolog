from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from movimentacoes.models import OrdemTransferencia, ItemOrdemTransferencia, Movimentacao
from movimentacoes.forms import OrdemTransferenciaForm
from produtos.models import Produto
from core.mixins import estoquista_ou_admin


@estoquista_ou_admin
def ordem_criar(request):
    form = OrdemTransferenciaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        origem = form.cleaned_data['local_origem']
        destino = form.cleaned_data['local_destino']

        produto_ids = request.POST.getlist('produto_id')
        quantidades = request.POST.getlist('quantidade')

        if not produto_ids:
            messages.error(request, 'Adicione pelo menos um produto.')
            return render(request, 'movimentacoes/ordem_transferencia/form.html', {
                'form': form,
                'produtos': Produto.objects.filter(ativo=True).order_by('nome'),
            })

        try:
            with transaction.atomic():
                ordem = OrdemTransferencia.objects.create(
                    numero=OrdemTransferencia.gerar_numero(),
                    local_origem=origem,
                    local_destino=destino,
                    observacao=form.cleaned_data['observacao'],
                    criado_por=request.user,
                )

                for pid, qtd in zip(produto_ids, quantidades):
                    if not pid or not qtd:
                        continue

                    produto = Produto.objects.get(pk=pid)
                    quantidade = Decimal(str(qtd))

                    if quantidade <= 0:
                        continue

                    # Cria a Movimentacao de saída — ela mesma se encarrega de
                    # debitar o Estoque via _aplicar_movimentacao(), incluindo
                    # a validação de saldo insuficiente.
                    Movimentacao.objects.create(
                        produto=produto,
                        local=origem,
                        tipo=Movimentacao.TIPO_SAIDA,
                        motivo='transferencia',
                        quantidade=quantidade,
                        observacao=f'Envio — Ordem de Transferência {ordem.numero}',
                        usuario=request.user,
                    )

                    ItemOrdemTransferencia.objects.create(
                        ordem=ordem,
                        produto=produto,
                        quantidade=quantidade,
                    )

            messages.success(request, f'Ordem {ordem.numero} criada e em trânsito!')
            return redirect('movimentacoes:ordem_detalhe', pk=ordem.pk)

        except ValidationError as e:
            messages.error(request, f'Estoque insuficiente: {e.messages[0]}')
        except Exception as e:
            messages.error(request, f'Erro ao criar ordem: {e}')

    return render(request, 'movimentacoes/ordem_transferencia/form.html', {
        'form': form,
        'produtos': Produto.objects.filter(ativo=True).order_by('nome'),
    })


@login_required
def ordem_list(request):
    status = request.GET.get('status', '')
    ordens = OrdemTransferencia.objects.select_related(
        'local_origem', 'local_destino', 'criado_por'
    ).order_by('-data_envio')

    if status:
        ordens = ordens.filter(status=status)

    paginator = Paginator(ordens, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'movimentacoes/ordem_transferencia/list.html', {
        'ordens': page_obj,
        'page_obj': page_obj,
        'status': status,
        'status_choices': OrdemTransferencia.STATUS_CHOICES,
    })


@login_required
def ordem_detalhe(request, pk):
    ordem = get_object_or_404(OrdemTransferencia, pk=pk)
    itens = ordem.itens.select_related('produto')
    return render(request, 'movimentacoes/ordem_transferencia/detalhe.html', {
        'ordem': ordem,
        'itens': itens,
    })


@estoquista_ou_admin
def ordem_confirmar(request, pk):
    ordem = get_object_or_404(OrdemTransferencia, pk=pk)

    if request.method == 'POST':
        try:
            ordem.confirmar_recebimento(request.user)
            messages.success(request, f'Ordem {ordem.numero} confirmada com sucesso!')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('movimentacoes:ordem_detalhe', pk=ordem.pk)

    return render(request, 'movimentacoes/ordem_transferencia/confirmar.html', {
        'ordem': ordem,
        'itens': ordem.itens.select_related('produto'),
    })


@estoquista_ou_admin
def ordem_cancelar(request, pk):
    ordem = get_object_or_404(OrdemTransferencia, pk=pk)

    if request.method == 'POST':
        try:
            ordem.cancelar(request.user)
            messages.success(request, f'Ordem {ordem.numero} cancelada. Estoque revertido.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('movimentacoes:ordem_list')

    return redirect('movimentacoes:ordem_detalhe', pk=ordem.pk)


@login_required
def ordem_imprimir(request, pk):
    import qrcode
    from io import BytesIO
    import base64

    ordem = get_object_or_404(OrdemTransferencia, pk=pk)
    itens = ordem.itens.select_related('produto')

    # Gera QR Code
    url    = request.build_absolute_uri(f'/movimentacoes/ordem/{ordem.token_confirmacao}/confirmar-qr/')
    qr     = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img    = qr.make_image(fill_color='black', back_color='white')
    buf    = BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render(request, 'movimentacoes/ordem_transferencia/imprimir.html', {
        'ordem':  ordem,
        'itens':  itens,
        'qr_b64': qr_b64,
    })

@login_required
def ordem_confirmar_qr(request, token):
    ordem = get_object_or_404(OrdemTransferencia, token_confirmacao=token)

    # ── Já foi confirmada ──
    if ordem.status == OrdemTransferencia.STATUS_RECEBIDO:
        return render(request, 'movimentacoes/ordem_transferencia/qr_ja_confirmada.html', {
            'ordem': ordem,
        })

    # ── Cancelada ──
    if ordem.status == OrdemTransferencia.STATUS_CANCELADO:
        return render(request, 'movimentacoes/ordem_transferencia/qr_status_invalido.html', {
            'ordem': ordem,
        })

    # ── Confirmação ──
    if request.method == 'POST':
        try:
            ordem.confirmar_recebimento(request.user)
            messages.success(request, f'Ordem {ordem.numero} confirmada!')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('movimentacoes:ordem_confirmar_qr', token=token)

    return render(request, 'movimentacoes/ordem_transferencia/qr_confirmar.html', {
        'ordem': ordem,
        'itens': ordem.itens.select_related('produto'),
    })