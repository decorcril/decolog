from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.urls import reverse
from decimal import Decimal
from collections import defaultdict
from datetime import date
import json

from produtos.models import Produto
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.mixins import producao_ou_gerente
from ..models import RegistroCorte, ItemCorte, ProdutoCortado


def _redirect_create(pedido_pk):
    """Redireciona de volta pro formulário, preservando o pedido em contexto."""
    url = reverse('producao_corte:create')
    if pedido_pk:
        url += f'?pedido_pk={pedido_pk}'
    return redirect(url)


def _ler_produtos_com_chapas(post):
    """
    Lê a lista de produtos cortados nesta sessão, cada um com a(s) chapa(s)
    que consumiu. Um mesmo produto pode ter usado material de mais de uma
    chapa (ex: um cubo que leva acrílico branco E acrílico cristal).
    """
    produtos = []
    pi = 0
    while f'produto_produto_{pi}' in post:
        prod_id = post.get(f'produto_produto_{pi}')
        qty     = post.get(f'produto_quantidade_{pi}')
        if prod_id and qty:
            chapas = []
            ci = 0
            while f'produto_chapa_{pi}_produto_{ci}' in post:
                chapa_id  = post.get(f'produto_chapa_{pi}_produto_{ci}')
                chapa_qty = post.get(f'produto_chapa_{pi}_quantidade_{ci}')
                if chapa_id and chapa_qty:
                    chapas.append((chapa_id, Decimal(chapa_qty)))
                ci += 1
            produtos.append({
                'produto_id': prod_id,
                'quantidade': Decimal(qty),
                'chapas':     chapas,
            })
        pi += 1
    return produtos


def _agregar_chapas(produtos_com_chapas):
    """Soma o total de cada tipo de chapa usado, somando entre todos os produtos da sessão."""
    totais = defaultdict(Decimal)
    for p in produtos_com_chapas:
        for chapa_id, qty in p['chapas']:
            totais[chapa_id] += qty
    return list(totais.items())  # [(chapa_id, quantidade_total), ...]


def _validar_estoque_chapas(chapas_totais):
    """Confere se há saldo suficiente de cada chapa antes de gravar qualquer coisa."""
    for prod_id, quantidade in chapas_totais:
        produto = Produto.objects.get(pk=prod_id)
        disponivel = Estoque.objects.filter(
            produto=produto
        ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')

        if disponivel < quantidade:
            raise ValueError(
                f'Estoque insuficiente para {produto.nome}: '
                f'disponível {disponivel}, solicitado {quantidade}.'
            )


def _baixar_chapa(produto, quantidade, data_parsed, pedido, registro, usuario):
    """Debita a chapa do(s) estoque(s) com saldo, do maior pro menor."""
    restante = quantidade
    for estoque in Estoque.objects.filter(produto=produto, quantidade__gt=0).order_by('-quantidade'):
        if restante <= 0:
            break
        abate = min(estoque.quantidade, restante)
        Movimentacao.objects.create(
            produto=produto,
            local=estoque.local,
            tipo='saida',
            motivo='uso_interno',
            quantidade=abate,
            observacao=(
                f'Corte em {data_parsed.strftime("%d/%m/%Y")}'
                + (f' — Pedido {pedido.numero}' if pedido else '')
            ),
            usuario=usuario,
            registro_corte=registro,
        )
        restante -= abate


def _criar_pecas_cortadas(item_corte_referencia, produtos_com_chapas, pedido, observacao, usuario):
    """
    Cria um ProdutoCortado por unidade cortada de cada produto da sessão.
    item_corte_referencia satisfaz a FK obrigatória (todo ProdutoCortado
    precisa apontar pra um ItemCorte) — não implica que a peça veio
    especificamente daquela chapa. A rastreabilidade de quais chapas a
    sessão consumiu está no RegistroCorte (via item_corte.registro).
    """
    for p in produtos_com_chapas:
        produto_cortado = Produto.objects.get(pk=p['produto_id'])
        for _ in range(int(p['quantidade'])):
            ProdutoCortado.objects.create(
                item_corte  = item_corte_referencia,
                produto     = produto_cortado,
                pedido      = pedido,
                cortada_por = usuario,
                observacao  = observacao,
            )


def _notificar_aguardando_montagem(pedido):
    """Avisa o time de montagem assim que o pedido entra em 'assembling'."""
    from core.models.notificacao import Notificacao
    usuarios = Notificacao.usuarios_por_grupo(
        'Operador de Montagem', 'Supervisor de Montagem', 'Gerente'
    )
    Notificacao.notificar(pedido, Notificacao.Tipo.AGUARD_MONTAGEM, usuarios)


def _atualizar_status_pedido(pedido, request):
    """
    Após registrar o corte, reavalia o progresso do pedido:
    - Se tudo cortado -> ASSEMBLING (e notifica o time de montagem).
    - Se ainda falta algo -> permanece/volta para CUTTING.
    """
    pedido.refresh_from_db()
    progresso   = pedido.progresso_corte
    incompletos = [p for p in progresso if not p['completo']]

    if not incompletos:
        pedido.status = pedido.Status.ASSEMBLING
        pedido.save(update_fields=['status', 'atualizado_em'])
        _notificar_aguardando_montagem(pedido)
        messages.success(request, f'Corte completo! Pedido {pedido.numero} enviado para montagem.')
    else:
        pedido.status = pedido.Status.CUTTING
        pedido.save(update_fields=['status', 'atualizado_em'])
        faltam = ', '.join(
            f"{p['nome']} ({p['falta']} restante{'s' if p['falta'] > 1 else ''})"
            for p in incompletos
        )
        messages.warning(request, f'Corte parcial registrado. Faltam: {faltam}')


@producao_ou_gerente
def registro_corte_create(request):
    from vendas.models import Pedido

    pedido_pk = request.GET.get('pedido_pk') or request.POST.get('pedido_pk')
    pedido    = get_object_or_404(Pedido, pk=pedido_pk) if pedido_pk else None

    produtos_materiais = Produto.objects.filter(
        categoria__in=['chapa'], ativo=True
    ).order_by('nome')
    produtos_finais = Produto.objects.filter(
        categoria='produto_final', ativo=True
    ).order_by('nome')

    if request.method == 'POST':
        data_str   = request.POST.get('data')
        observacao = request.POST.get('observacao', '')

        try:
            data_parsed = date.fromisoformat(data_str)
        except (ValueError, TypeError):
            messages.error(request, 'Data inválida.')
            return _redirect_create(pedido_pk)

        if data_parsed > timezone.localdate():
            messages.error(request, 'A data não pode ser no futuro.')
            return _redirect_create(pedido_pk)

        produtos_com_chapas = _ler_produtos_com_chapas(request.POST)

        if not produtos_com_chapas:
            messages.error(request, 'Informe ao menos um produto cortado.')
            return _redirect_create(pedido_pk)

        if not any(p['chapas'] for p in produtos_com_chapas):
            messages.error(request, 'Informe ao menos uma chapa utilizada.')
            return _redirect_create(pedido_pk)

        chapas_totais = _agregar_chapas(produtos_com_chapas)

        try:
            from django.db import transaction
            with transaction.atomic():
                _validar_estoque_chapas(chapas_totais)

                registro = RegistroCorte.objects.create(
                    data=data_parsed,
                    operador=request.user,
                    observacao=observacao,
                    pedido=pedido,
                )

                item_corte_referencia = None
                for prod_id, quantidade in chapas_totais:
                    produto_chapa = Produto.objects.get(pk=prod_id)

                    _baixar_chapa(produto_chapa, quantidade, data_parsed, pedido, registro, request.user)

                    item_corte = ItemCorte.objects.create(
                        registro=registro,
                        chapa=produto_chapa,
                        quantidade_chapa=quantidade,
                    )
                    if item_corte_referencia is None:
                        item_corte_referencia = item_corte

                _criar_pecas_cortadas(
                    item_corte_referencia, produtos_com_chapas, pedido, observacao, request.user,
                )

                if pedido:
                    _atualizar_status_pedido(pedido, request)

                messages.success(request, 'Registro de corte salvo com sucesso!')
                return redirect('producao_corte:list')

        except ValueError as e:
            messages.error(request, str(e))
            return _redirect_create(pedido_pk)

    # ── GET: monta o formulário ──
    produtos_pedido = []
    if pedido:
        for p in pedido.progresso_corte:
            if not p['completo']:
                item = pedido.itens.filter(produto__nome=p['nome']).first()
                if item:
                    produtos_pedido.append({
                        'id':         str(item.produto.pk),
                        'nome':       p['nome'],
                        'quantidade': float(p['falta']),
                    })

    return render(request, 'producao_corte/registro_corte_form.html', {
        'hoje':           timezone.localdate().isoformat(),
        'materiais_json': json.dumps([
            {'id': str(p.pk), 'nome': p.nome, 'codigo': p.codigo or ''}
            for p in produtos_materiais
        ], ensure_ascii=False),
        'produtos_json': json.dumps([
            {'id': str(p.pk), 'nome': p.nome, 'codigo': p.codigo or ''}
            for p in produtos_finais
        ], ensure_ascii=False),
        'pedido':          pedido,
        'pedido_pk':       pedido_pk or '',
        'produtos_pedido': json.dumps(produtos_pedido, ensure_ascii=False),
    })


@producao_ou_gerente
def registro_corte_list(request):
    is_supervisor = (
        request.user.is_staff or
        request.user.groups.filter(
            name__in=['Supervisor de Laser', 'Gerente']
        ).exists()
    )

    if is_supervisor:
        registros = RegistroCorte.objects.all()
    else:
        registros = RegistroCorte.objects.filter(operador=request.user)

    operador_id   = request.GET.get('operador', '')
    data_inicio   = request.GET.get('data_inicio', '')
    data_fim      = request.GET.get('data_fim', '')
    pedido_numero = request.GET.get('pedido', '')

    if is_supervisor and operador_id:
        registros = registros.filter(operador__id=operador_id)

    if data_inicio:
        registros = registros.filter(data__gte=data_inicio)
    if data_fim:
        registros = registros.filter(data__lte=data_fim)
    if pedido_numero:
        registros = registros.filter(pedido__numero__icontains=pedido_numero)

    registros = registros.prefetch_related(
        'itens__chapa', 'itens__produtos_cortados__produto'
    ).select_related('operador').annotate(
        total_chapas=Sum('itens__quantidade_chapa')
    ).order_by('-data', '-criado_em')

    paginator   = Paginator(registros, 20)
    page_number = request.GET.get('page')
    page_obj    = paginator.get_page(page_number)

    operadores = User.objects.filter(
        registrocorte__isnull=False
    ).distinct() if is_supervisor else None

    return render(request, 'producao_corte/registro_corte_list.html', {
        'registros':     page_obj,
        'is_supervisor': is_supervisor,
        'operadores':    operadores,
        'operador_id':   operador_id,
        'data_inicio':   data_inicio,
        'data_fim':      data_fim,
        'pedido_numero': pedido_numero,
        'page_obj':      page_obj,
    })


@producao_ou_gerente
def registro_corte_delete(request, pk):
    registro = get_object_or_404(RegistroCorte, pk=pk)

    if request.method == 'POST':
        try:
            from django.db import transaction
            with transaction.atomic():
                for mov in registro.movimentacoes.all():
                    Movimentacao.objects.create(
                        produto=mov.produto,
                        local=mov.local,
                        tipo='entrada',
                        motivo='uso_interno',
                        quantidade=mov.quantidade,
                        observacao=f'Estorno do corte em {registro.data.strftime("%d/%m/%Y")}',
                        usuario=request.user,
                    )
                registro.delete()
                messages.success(request, 'Registro excluído e estoque estornado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {e}')

        return redirect('producao_corte:list')

    return render(request, 'producao_corte/registro_corte_confirm_delete.html', {
        'registro': registro,
    })


@producao_ou_gerente
def registro_corte_detail(request, pk):
    registro = get_object_or_404(
        RegistroCorte.objects.prefetch_related('itens__chapa').select_related('operador'),
        pk=pk
    )
    produtos_cortados = ProdutoCortado.objects.filter(
        item_corte__registro=registro,
    ).select_related('produto').order_by('produto__nome', 'id')

    is_supervisor = (
        request.user.is_staff or
        request.user.groups.filter(
            name__in=['Supervisor de Laser', 'Gerente']
        ).exists()
    )
    operador_id = request.GET.get('operador', '')
    page        = request.GET.get('page', '')

    return render(request, 'producao_corte/registro_corte_detail.html', {
        'registro':          registro,
        'produtos_cortados': produtos_cortados,
        'is_supervisor':      is_supervisor,
        'operador_id':        operador_id,
        'page':                page,
    })