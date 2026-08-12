# financeiro/views/contas_pagar.py
import datetime
import uuid
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.mixins import financeiro_ou_gerente
from core.models import Fornecedor
from financeiro.models import (
    ContaPagar,
    ContaPagarParcela,
    PagamentoContaPagar,
)


def _parse_decimal(val, default='0'):
    try:
        return Decimal((val or default).replace('.', '').replace(',', '.'))
    except Exception:
        return Decimal(default)


def _parse_competencia(raw, fallback_data_emissao):
    """Converte 'AAAA-MM' (input type=month) em date do dia 1. Cai pro mês da emissão se vazio."""
    if raw:
        try:
            ano, mes = raw.split('-')
            return datetime.date(int(ano), int(mes), 1)
        except (ValueError, AttributeError):
            pass
    if fallback_data_emissao:
        data = datetime.date.fromisoformat(fallback_data_emissao)
        return data.replace(day=1)
    return None


def _criar_parcelas_manual(conta, valores_raw, vencimentos_raw):
    """Cria uma parcela por linha da grade enviada pelo operador (valor e vencimento próprios)."""
    for i, (valor_raw, venc_raw) in enumerate(zip(valores_raw, vencimentos_raw), start=1):
        ContaPagarParcela.objects.create(
            conta=conta,
            numero=i,
            vencimento=datetime.date.fromisoformat(venc_raw),
            valor=_parse_decimal(valor_raw),
        )


def _validar_grade_parcelas(valores_raw, vencimentos_raw, valor_total):
    """Valida a grade manual: mesma quantidade de valores/vencimentos, todos preenchidos,
    valores positivos, e soma batendo exatamente com o valor total da conta."""
    if not valores_raw or not vencimentos_raw:
        return 'Adicione ao menos uma parcela.'
    if len(valores_raw) != len(vencimentos_raw):
        return 'Cada parcela precisa ter valor e vencimento.'

    soma = Decimal('0')
    for valor_raw, venc_raw in zip(valores_raw, vencimentos_raw):
        if not venc_raw:
            return 'Preencha o vencimento de todas as parcelas.'
        try:
            datetime.date.fromisoformat(venc_raw)
        except ValueError:
            return 'Vencimento inválido em uma das parcelas.'

        valor = _parse_decimal(valor_raw)
        if valor <= 0:
            return 'Todas as parcelas precisam de valor maior que zero.'
        soma += valor

    if soma != valor_total:
        return f'A soma das parcelas ({soma}) não bate com o valor total ({valor_total}).'

    return None


@financeiro_ou_gerente
def conta_pagar_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    fornecedor_id = request.GET.get('fornecedor', '')
    categoria = request.GET.get('categoria', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    contas = (
        ContaPagar.objects
        .select_related('fornecedor')
        .prefetch_related('parcelas__pagamentos')
        .all()
    )

    if q:
        contas = contas.filter(
            Q(descricao__icontains=q) | Q(numero_documento__icontains=q)
        )
    if fornecedor_id:
        contas = contas.filter(fornecedor_id=fornecedor_id)
    if categoria:
        contas = contas.filter(categoria=categoria)
    if data_inicio:
        contas = contas.filter(data_emissao__gte=data_inicio)
    if data_fim:
        contas = contas.filter(data_emissao__lte=data_fim)

    contas = contas.order_by('-data_emissao')

    # Status é calculado (status_efetivo das parcelas), não é campo do banco —
    # filtra em Python depois de já ter aplicado os outros filtros no queryset.
    # 'a_vencer' é um valor sintético: não existe como status_efetivo (que só tem
    # 'aberto'), então trata separado — filtra contas com pelo menos uma parcela
    # 'aberto' com vencimento no futuro, e nenhuma parcela vencida no meio.
    if status:
        contas = [c for c in contas if c.status == status]
        
    hoje = timezone.localdate()

    total_vencido = ContaPagarParcela.objects.filter(
        status=ContaPagarParcela.Status.ABERTO,
        vencimento__lt=hoje,
    ).aggregate(t=Sum('valor'))['t'] or 0

    total_a_vencer = ContaPagarParcela.objects.filter(
        status=ContaPagarParcela.Status.ABERTO,
        vencimento__gte=hoje,
    ).aggregate(t=Sum('valor'))['t'] or 0

    resumo = {
        'total_aberto': total_vencido + total_a_vencer,
        'total_vencido': total_vencido,
        'total_a_vencer': total_a_vencer,
        'total_a_vencer_7dias': ContaPagarParcela.objects.filter(
            status=ContaPagarParcela.Status.ABERTO,
            vencimento__range=[hoje, hoje + datetime.timedelta(days=7)],
        ).aggregate(t=Sum('valor'))['t'] or 0,
        'total_pago_mes': PagamentoContaPagar.objects.filter(
            data_pagamento__month=hoje.month,
            data_pagamento__year=hoje.year,
        ).aggregate(t=Sum('valor_pago'))['t'] or 0,
        'total_juros_multa_mes': PagamentoContaPagar.objects.filter(
            data_pagamento__month=hoje.month,
            data_pagamento__year=hoje.year,
        ).aggregate(t=Sum('juros_multa'))['t'] or 0,
    }

    paginator = Paginator(contas, 20)
    contas = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'financeiro/contas_pagar/list.html', {
        'contas': contas,
        'q': q,
        'status': status,
        'categoria': categoria,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'status_choices': ContaPagarParcela.Status.choices,
        'categoria_choices': ContaPagar.Categoria.choices,
        'fornecedores': Fornecedor.objects.all().order_by('nome'),
        'resumo': resumo,
    })

@financeiro_ou_gerente
def conta_pagar_create(request):
    if request.method == 'POST':
        form_token = request.POST.get('form_token', '')
        token_usado = request.session.get('ultimo_form_token_conta')

        if form_token and form_token == token_usado:
            messages.warning(request, 'Essa conta já havia sido criada (envio duplicado ignorado).')
            return redirect('financeiro:contas_pagar_list')

        fornecedor_id = request.POST.get('fornecedor')
        categoria = request.POST.get('categoria', '')
        valor_total = _parse_decimal(request.POST.get('valor_total', '0'))
        data_emissao_raw = request.POST.get('data_emissao')
        competencia_raw = request.POST.get('competencia', '')

        parcela_valores_raw = request.POST.getlist('parcela_valor[]')
        parcela_vencimentos_raw = request.POST.getlist('parcela_vencimento[]')

        erro = None
        if not fornecedor_id:
            erro = 'Selecione um fornecedor.'
        elif not request.POST.get('descricao', '').strip():
            erro = 'Informe a descrição.'
        elif valor_total <= 0:
            erro = 'Valor total deve ser maior que zero.'
        elif not data_emissao_raw:
            erro = 'Informe a data de emissão.'
        else:
            erro = _validar_grade_parcelas(parcela_valores_raw, parcela_vencimentos_raw, valor_total)

        if erro:
            messages.error(request, erro)
            return render(request, 'financeiro/contas_pagar/form.html', {
                'titulo': 'Nova Conta a Pagar',
                'fornecedores': Fornecedor.objects.all().order_by('nome'),
                'categoria_choices': ContaPagar.Categoria.choices,
                'form_token': form_token or str(uuid.uuid4()),
            })

        conta = ContaPagar.objects.create(
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            descricao=request.POST.get('descricao', '').strip(),
            numero_documento=request.POST.get('numero_documento', ''),
            competencia=_parse_competencia(competencia_raw, data_emissao_raw),
            data_emissao=data_emissao_raw,
            valor_total=valor_total,
            observacoes=request.POST.get('observacoes', ''),
            criado_por=request.user,
        )

        _criar_parcelas_manual(conta, parcela_valores_raw, parcela_vencimentos_raw)

        if form_token:
            request.session['ultimo_form_token_conta'] = form_token

        messages.success(request, 'Conta a pagar criada com sucesso!')
        return redirect('financeiro:contas_pagar_detail', pk=conta.pk)

    return render(request, 'financeiro/contas_pagar/form.html', {
        'titulo': 'Nova Conta a Pagar',
        'fornecedores': Fornecedor.objects.all().order_by('nome'),
        'categoria_choices': ContaPagar.Categoria.choices,
        'form_token': str(uuid.uuid4()),
    })


@financeiro_ou_gerente
def conta_pagar_edit(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    tem_pagamento = PagamentoContaPagar.objects.filter(parcela__conta=conta).exists()

    if request.method == 'POST':
        fornecedor_id = request.POST.get('fornecedor')
        categoria = request.POST.get('categoria', '')
        valor_total = _parse_decimal(request.POST.get('valor_total', '0'))
        data_emissao_raw = request.POST.get('data_emissao')
        competencia_raw = request.POST.get('competencia', '')

        parcela_valores_raw = request.POST.getlist('parcela_valor[]')
        parcela_vencimentos_raw = request.POST.getlist('parcela_vencimento[]')

        erro = None
        if not fornecedor_id:
            erro = 'Selecione um fornecedor.'
        elif not request.POST.get('descricao', '').strip():
            erro = 'Informe a descrição.'
        elif valor_total <= 0:
            erro = 'Valor total deve ser maior que zero.'
        elif not data_emissao_raw:
            erro = 'Informe a data de emissão.'
        elif not tem_pagamento:
            erro = _validar_grade_parcelas(parcela_valores_raw, parcela_vencimentos_raw, valor_total)

        if erro:
            messages.error(request, erro)
            return render(request, 'financeiro/contas_pagar/form.html', {
                'titulo': f'Editar: {conta.descricao}',
                'conta': conta,
                'parcelas': conta.parcelas.all(),
                'tem_pagamento': tem_pagamento,
                'fornecedores': Fornecedor.objects.all().order_by('nome'),
                'categoria_choices': ContaPagar.Categoria.choices,
                'form_token': str(uuid.uuid4()),
            })

        conta.fornecedor_id = fornecedor_id
        conta.categoria = categoria
        conta.descricao = request.POST.get('descricao', '').strip()
        conta.numero_documento = request.POST.get('numero_documento', '')
        conta.competencia = _parse_competencia(competencia_raw, data_emissao_raw)
        conta.data_emissao = data_emissao_raw

        if not tem_pagamento:
            conta.valor_total = valor_total

        conta.observacoes = request.POST.get('observacoes', '')
        conta.save()

        if not tem_pagamento:
            # Sem pagamento registrado ainda: seguro reconstruir as parcelas do zero.
            conta.parcelas.all().delete()
            _criar_parcelas_manual(conta, parcela_valores_raw, parcela_vencimentos_raw)

        messages.success(request, 'Conta atualizada com sucesso!')
        return redirect('financeiro:contas_pagar_detail', pk=conta.pk)

    return render(request, 'financeiro/contas_pagar/form.html', {
        'titulo': f'Editar: {conta.descricao}',
        'conta': conta,
        'parcelas': conta.parcelas.all(),
        'tem_pagamento': tem_pagamento,
        'fornecedores': Fornecedor.objects.all().order_by('nome'),
        'categoria_choices': ContaPagar.Categoria.choices,
        'form_token': str(uuid.uuid4()),
    })

@financeiro_ou_gerente
def conta_pagar_delete(request, pk):
    """Exclui a conta permanentemente — inclui parcelas e pagamentos em cascata."""
    conta = get_object_or_404(ContaPagar, pk=pk)

    if request.method == 'POST':
        descricao = conta.descricao
        conta.delete()
        messages.success(request, f'Conta "{descricao}" excluída.')
        return redirect('financeiro:contas_pagar_list')

    return redirect('financeiro:contas_pagar_detail', pk=conta.pk)


@financeiro_ou_gerente
def conta_pagar_detail(request, pk):
    conta = get_object_or_404(
        ContaPagar.objects
        .select_related('fornecedor')
        .prefetch_related('parcelas__pagamentos'),
        pk=pk
    )
    return render(request, 'financeiro/contas_pagar/detail.html', {
        'conta': conta,
        'parcelas': conta.parcelas.all(),
    })


@financeiro_ou_gerente
def pagamento_parcela_add(request, conta_pk, parcela_pk):
    parcela = get_object_or_404(ContaPagarParcela, pk=parcela_pk, conta_id=conta_pk)

    if request.method == 'POST':
        valor = _parse_decimal(request.POST.get('valor_pago', '0'))
        juros_multa = _parse_decimal(request.POST.get('juros_multa', '0'))
        forma = request.POST.get('forma_pagamento', '')
        data_pagamento = request.POST.get('data_pagamento') or timezone.localdate()

        ha_pouco = timezone.now() - datetime.timedelta(seconds=10)
        ja_existe = PagamentoContaPagar.objects.filter(
            parcela=parcela,
            valor_pago=valor,
            data_pagamento=data_pagamento,
            forma_pagamento=forma,
            criado_em__gte=ha_pouco,
        ).exists()

        if ja_existe:
            messages.warning(request, 'Esse pagamento já foi registrado agora há pouco (envio duplicado ignorado).')
            return redirect('financeiro:contas_pagar_detail', pk=conta_pk)

        if valor <= 0:
            messages.error(request, 'O valor do pagamento deve ser maior que zero.')
        elif not forma:
            messages.error(request, 'Selecione a forma de pagamento.')
        else:
            try:
                PagamentoContaPagar.objects.create(
                    parcela=parcela,
                    valor_pago=valor,
                    juros_multa=juros_multa,
                    data_pagamento=data_pagamento,
                    forma_pagamento=forma,
                    transacao=request.POST.get('transacao', ''),
                    observacao=request.POST.get('observacao', ''),
                    criado_por=request.user,
                )
                messages.success(request, f'Pagamento da parcela {parcela.numero} registrado!')
            except ValidationError as e:
                erro = e.messages[0] if getattr(e, 'messages', None) else str(e)
                messages.error(request, erro)

    return redirect('financeiro:contas_pagar_detail', pk=conta_pk)


@financeiro_ou_gerente
def pagamento_parcela_delete(request, conta_pk, parcela_pk, pag_pk):
    parcela = get_object_or_404(ContaPagarParcela, pk=parcela_pk, conta_id=conta_pk)
    pagamento = get_object_or_404(PagamentoContaPagar, pk=pag_pk, parcela=parcela)

    if request.method == 'POST':
        pagamento.delete()
        messages.success(request, 'Pagamento removido.')

    return redirect('financeiro:contas_pagar_detail', pk=conta_pk)


@financeiro_ou_gerente
def conta_pagar_cancelar(request, pk):
    """Cancela a conta inteira — marca todas as parcelas ainda não pagas como canceladas."""
    conta = get_object_or_404(ContaPagar, pk=pk)

    if request.method == 'POST':
        conta.parcelas.exclude(status=ContaPagarParcela.Status.PAGO).update(
            status=ContaPagarParcela.Status.CANCELADO
        )
        messages.success(request, f'Conta "{conta.descricao}" cancelada.')

    return redirect('financeiro:contas_pagar_detail', pk=conta.pk)