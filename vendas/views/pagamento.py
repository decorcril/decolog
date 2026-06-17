from decimal import Decimal
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError

from vendas.models import Pedido
from vendas.models.pagamento import Pagamento
from core.mixins import financeiro_ou_gerente


@financeiro_ou_gerente
def pagamento_add(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        metodo    = request.POST.get('metodo', '')
        valor_raw = request.POST.get('valor', '0')
        transacao = request.POST.get('transacao', '').strip() or None

        # Limpa máscara: 1.500,00 → 1500.00
        valor_limpo = valor_raw.replace('.', '').replace(',', '.')
        try:
            valor = Decimal(valor_limpo)
        except Exception:
            messages.error(request, 'Valor inválido.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)

        if valor <= 0:
            messages.error(request, 'O valor do pagamento deve ser maior que zero.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)

        if metodo != 'cash' and not transacao:
            messages.error(request, 'O número de transação é obrigatório para esta forma de pagamento.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)

        try:
            Pagamento.objects.create(
                pedido     = pedido,
                metodo     = metodo,
                valor      = valor,
                transacao  = transacao,
                criado_por = request.user,
            )
            messages.success(request, 'Pagamento registrado com sucesso!')
        except ValidationError as e:
            erro = list(e.message_dict.values())[0][0] if hasattr(e, 'message_dict') else e.messages[0]
            messages.error(request, erro)
        except Exception as e:
            messages.error(request, f'Erro ao registrar pagamento: {e}')

    return redirect('vendas:pedido_detail', pk=pedido.pk)


@financeiro_ou_gerente
def pagamento_delete(request, pk, pag_pk):
    pedido    = get_object_or_404(Pedido, pk=pk)
    pagamento = get_object_or_404(Pagamento, pk=pag_pk, pedido=pedido)

    if request.method == 'POST':
        pagamento.delete()
        messages.success(request, 'Pagamento removido.')

    return redirect('vendas:pedido_detail', pk=pedido.pk)