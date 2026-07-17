from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from producao_corte.models import ProdutoCortado
from movimentacoes.models import Movimentacao
from core.models import Local


@login_required
def peca_scan(request, token):
    peca = get_object_or_404(ProdutoCortado, token=token)

    # ── Já montada ──
    if peca.status == 'montado':
        return render(request, 'producao_corte/peca_ja_montada.html', {'peca': peca})

    # ── Confirmação de montagem ──
    if request.method == 'POST':
        fabrica = Local.objects.filter(tipo='fabrica').first()

        try:
            ficha = peca.produto.ficha_tecnica
            for componente in ficha.itens.select_related('material').all():
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = fabrica,
                    tipo       = 'entrada',
                    motivo     = 'producao',
                    quantidade = componente.quantidade,
                    observacao = f'Montagem — {peca.produto.nome}',
                    usuario    = request.user,
                )
        except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            Movimentacao.objects.create(
                produto    = peca.produto,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = 1,
                observacao = f'Montagem — {peca.produto.nome}',
                usuario    = request.user,
            )

        peca.status      = 'montado'
        peca.montada_por = request.user
        peca.montada_em  = timezone.now()
        peca.save(update_fields=['status', 'montada_por', 'montada_em'])

        # ── Verifica se todas as peças do pedido foram montadas ──
        if peca.pedido:
            pedido   = peca.pedido
            total    = ProdutoCortado.objects.filter(pedido=pedido).count()
            montadas = ProdutoCortado.objects.filter(pedido=pedido, status='montado').count()

            if total > 0 and montadas >= total:
                pedido.status = pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])

        return render(request, 'producao_corte/peca_montada.html', {
            'peca':   peca,
            'pedido': peca.pedido,
        })

    return render(request, 'producao_corte/peca_confirmar.html', {'peca': peca})