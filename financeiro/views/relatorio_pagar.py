# financeiro/views/relatorio_pagar.py
import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from core.mixins import financeiro_ou_gerente
from core.models import Fornecedor
from financeiro.models import ContaPagar, ContaPagarParcela

ZERO = Decimal('0')
DEC  = DecimalField(max_digits=12, decimal_places=2)

STATUS_CHOICES = [
    ('em_aberto', 'Em aberto'),
    ('vencido',   'Vencidas'),
    ('a_vencer',  'A vencer'),
    ('parcial',   'Pagas parcialmente'),
    ('pago',      'Pagas'),
    ('cancelado', 'Canceladas'),
    ('todos',     'Todas'),
]

# situação -> (rótulo, cor no PDF)
SITUACOES = {
    'vencido':   ('Vencido',   '#c0392b'),
    'a_vencer':  ('A vencer',  '#b9770e'),
    'parcial':   ('Parcial',   '#1f618d'),
    'pago':      ('Pago',      '#1e8449'),
    'cancelado': ('Cancelado', '#7f8c8d'),
}


def _parse_data(raw):
    try:
        return datetime.date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _situacao(parcela, hoje):
    """Situação para o relatório. Parcela aberta ou parcial com vencimento
    passado é 'vencido' (o saldo que resta está em atraso)."""
    S = ContaPagarParcela.Status
    if parcela.status == S.CANCELADO:
        return 'cancelado'
    if parcela.status == S.PAGO:
        return 'pago'
    if parcela.vencimento < hoje:
        return 'vencido'
    if parcela.status == S.PARCIAL:
        return 'parcial'
    return 'a_vencer'


def _montar_relatorio(request):
    """Aplica os filtros do GET e devolve linhas + totais.
    Usado pela tela e pelo PDF, pra os dois mostrarem exatamente o mesmo."""
    hoje = timezone.localdate()
    S = ContaPagarParcela.Status

    status       = request.GET.get('status') or 'em_aberto'
    fornecedor   = request.GET.get('fornecedor', '')
    categoria    = request.GET.get('categoria', '')
    venc_de_dt   = _parse_data(request.GET.get('venc_de', ''))
    venc_ate_dt  = _parse_data(request.GET.get('venc_ate', ''))

    if status not in dict(STATUS_CHOICES):
        status = 'em_aberto'

    parcelas = (
        ContaPagarParcela.objects
        .select_related('conta', 'conta__fornecedor')
        .annotate(
            pago_ann=Coalesce(Sum('pagamentos__valor_pago'), ZERO, output_field=DEC),
            juros_ann=Coalesce(Sum('pagamentos__juros_multa'), ZERO, output_field=DEC),
        )
    )

    if status == 'em_aberto':
        parcelas = parcelas.filter(status__in=[S.ABERTO, S.PARCIAL])
    elif status == 'vencido':
        parcelas = parcelas.filter(status__in=[S.ABERTO, S.PARCIAL], vencimento__lt=hoje)
    elif status == 'a_vencer':
        parcelas = parcelas.filter(status=S.ABERTO, vencimento__gte=hoje)
    elif status == 'parcial':
        parcelas = parcelas.filter(status=S.PARCIAL, vencimento__gte=hoje)
    elif status in ('pago', 'cancelado'):
        parcelas = parcelas.filter(status=status)
    # 'todos': sem filtro de situação

    fornecedor_nome = ''
    if fornecedor.isdigit():
        parcelas = parcelas.filter(conta__fornecedor_id=int(fornecedor))
        fornecedor_nome = (
            Fornecedor.objects.filter(pk=int(fornecedor))
            .values_list('nome', flat=True).first() or ''
        )
    if categoria in dict(ContaPagar.Categoria.choices):
        parcelas = parcelas.filter(conta__categoria=categoria)
    if venc_de_dt:
        parcelas = parcelas.filter(vencimento__gte=venc_de_dt)
    if venc_ate_dt:
        parcelas = parcelas.filter(vencimento__lte=venc_ate_dt)

    parcelas = list(
        parcelas.order_by('vencimento', 'conta__fornecedor__nome', 'conta_id', 'numero')
    )

    # Quantas parcelas cada conta tem (pra mostrar "2/5"), em uma query só.
    conta_ids = {p.conta_id for p in parcelas}
    contagem = dict(
        ContaPagarParcela.objects.filter(conta_id__in=conta_ids)
        .order_by().values('conta_id').annotate(c=Count('id'))
        .values_list('conta_id', 'c')
    )

    tot = {k: ZERO for k in ('valor', 'pago', 'juros', 'saldo', 'vencido', 'a_vencer')}
    linhas = []
    for p in parcelas:
        situacao = _situacao(p, hoje)
        if situacao in ('pago', 'cancelado'):
            saldo = ZERO
        else:
            saldo = max(p.valor - p.pago_ann, ZERO)

        linhas.append({
            'parcela':         p,
            'conta':           p.conta,
            'fornecedor':      p.conta.fornecedor.nome,
            'n_parcelas':      contagem.get(p.conta_id, 1),
            'pago':            p.pago_ann,
            'saldo':           saldo,
            'situacao':        situacao,
            'situacao_label':  SITUACOES[situacao][0],
        })

        if situacao != 'cancelado':
            tot['valor'] += p.valor
            tot['pago']  += p.pago_ann
            tot['juros'] += p.juros_ann
        tot['saldo'] += saldo
        if situacao == 'vencido':
            tot['vencido'] += saldo
        elif situacao in ('a_vencer', 'parcial'):
            tot['a_vencer'] += saldo

    return {
        'linhas':            linhas,
        'tot':               tot,
        'hoje':              hoje,
        'status':            status,
        'fornecedor':        fornecedor,
        'fornecedor_nome':   fornecedor_nome,
        'categoria':         categoria,
        'venc_de':           venc_de_dt.isoformat() if venc_de_dt else '',
        'venc_ate':          venc_ate_dt.isoformat() if venc_ate_dt else '',
        'venc_de_dt':        venc_de_dt,
        'venc_ate_dt':       venc_ate_dt,
        'status_choices':    STATUS_CHOICES,
        'categoria_choices': ContaPagar.Categoria.choices,
        'fornecedores':      Fornecedor.objects.all().order_by('nome'),
        'querystring':       request.GET.urlencode(),
    }


@financeiro_ou_gerente
def relatorio_pagar(request):
    return render(request, 'financeiro/contas_pagar/relatorio.html', _montar_relatorio(request))


@financeiro_ou_gerente
def relatorio_pagar_pdf(request):
    # Imports aqui dentro: evita dependência circular entre apps na hora de subir o Django.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from vendas.views.pdf import (
        C_BORDER, C_LIGHT_BG, C_TOTAL_BG, C_WHITE, MARGIN,
        _fmt_brl, _section_title, _styles,
    )

    ctx = _montar_relatorio(request)
    tot = ctx['tot']
    s   = _styles()

    page_w, _page_h = landscape(A4)
    content_w = page_w - 2 * MARGIN

    agora   = timezone.localtime().strftime('%d/%m/%Y  %H:%M')
    usuario = request.user.get_full_name() or request.user.username

    # ── Texto dos filtros aplicados ──
    de, ate = ctx['venc_de_dt'], ctx['venc_ate_dt']
    if de and ate:
        periodo = f"{de:%d/%m/%Y} a {ate:%d/%m/%Y}"
    elif de:
        periodo = f"a partir de {de:%d/%m/%Y}"
    elif ate:
        periodo = f"até {ate:%d/%m/%Y}"
    else:
        periodo = 'qualquer data'

    status_label = dict(STATUS_CHOICES)[ctx['status']]
    cat_label    = dict(ContaPagar.Categoria.choices).get(ctx['categoria'], 'Todas')
    forn_label   = ctx['fornecedor_nome'] or 'Todos'

    filtros = (
        f"<b>Situação:</b> {escape(status_label)} &nbsp;|&nbsp; "
        f"<b>Vencimento:</b> {escape(periodo)} &nbsp;|&nbsp; "
        f"<b>Fornecedor:</b> {escape(forn_label)} &nbsp;|&nbsp; "
        f"<b>Categoria:</b> {escape(cat_label)}"
    )

    el = []

    # ── Cabeçalho ──
    header = Table(
        [[
            [Paragraph('RELATÓRIO DE CONTAS A PAGAR', s['company'])],
            [Paragraph(f'Emissão: {agora}', s['doc_label']),
             Paragraph(f'Por: {escape(usuario)}', s['doc_label'])],
        ]],
        colWidths=[content_w * 0.65, content_w * 0.35],
    )
    header.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
    ]))
    el.append(header)
    el.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceBefore=2 * mm, spaceAfter=3 * mm))
    el.append(Paragraph(filtros, s['td']))
    el.append(Spacer(1, 4 * mm))

    # ── Resumo ──
    el.append(_section_title('Resumo', s))
    el.append(Spacer(1, 2 * mm))
    resumo = Table(
        [
            [Paragraph(t, s['th_c']) for t in
             ('Saldo a pagar', 'Vencido', 'A vencer', 'Pago', 'Juros/multa pagos')],
            [Paragraph(f'<b>{_fmt_brl(v)}</b>', s['td_c']) for v in
             (tot['saldo'], tot['vencido'], tot['a_vencer'], tot['pago'], tot['juros'])],
        ],
        colWidths=[content_w / 5] * 5,
    )
    resumo.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  C_LIGHT_BG),
        ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    el.append(resumo)
    el.append(Spacer(1, 5 * mm))

    # ── Parcelas ──
    el.append(_section_title('Parcelas', s))
    el.append(Spacer(1, 2 * mm))

    linhas = ctx['linhas']
    if not linhas:
        el.append(Paragraph('Nenhuma parcela encontrada com os filtros selecionados.', s['td']))
    else:
        c_venc, c_parc, c_cat = 22 * mm, 14 * mm, 28 * mm
        c_val, c_pago, c_saldo, c_sit = 26 * mm, 26 * mm, 26 * mm, 24 * mm
        resto  = content_w - (c_venc + c_parc + c_cat + c_val + c_pago + c_saldo + c_sit)
        c_forn = resto * 0.40
        c_desc = resto * 0.60

        dados = [[
            Paragraph('Vencimento', s['th_c']), Paragraph('Fornecedor', s['th']),
            Paragraph('Descrição / Documento', s['th']), Paragraph('Parc.', s['th_c']),
            Paragraph('Categoria', s['th']), Paragraph('Valor', s['th_c']),
            Paragraph('Pago', s['th_c']), Paragraph('Saldo', s['th_c']),
            Paragraph('Situação', s['th_c']),
        ]]

        for l in linhas:
            conta = l['conta']
            desc  = escape(conta.descricao)
            if conta.numero_documento:
                desc += (f' <font size="7" color="#666666">'
                         f'Doc. {escape(conta.numero_documento)}</font>')
            nome_sit, cor = SITUACOES[l['situacao']]
            dados.append([
                Paragraph(l['parcela'].vencimento.strftime('%d/%m/%Y'), s['td_c']),
                Paragraph(escape(l['fornecedor']), s['td']),
                Paragraph(desc, s['td']),
                Paragraph(f"{l['parcela'].numero}/{l['n_parcelas']}", s['td_c']),
                Paragraph(escape(conta.get_categoria_display() or '—'), s['td']),
                Paragraph(_fmt_brl(l['parcela'].valor), s['td_r']),
                Paragraph(_fmt_brl(l['pago']), s['td_r']),
                Paragraph(_fmt_brl(l['saldo']), s['td_r_bold']),
                Paragraph(f'<font color="{cor}"><b>{nome_sit}</b></font>', s['td_c']),
            ])

        dados.append([
            Paragraph('TOTAL', s['td_r_bold']), '', '', '', '',
            Paragraph(_fmt_brl(tot['valor']), s['td_r_bold']),
            Paragraph(_fmt_brl(tot['pago']), s['td_r_bold']),
            Paragraph(_fmt_brl(tot['saldo']), s['td_r_bold']),
            '',
        ])

        ult = len(dados) - 1
        tabela = Table(
            dados, repeatRows=1,
            colWidths=[c_venc, c_forn, c_desc, c_parc, c_cat, c_val, c_pago, c_saldo, c_sit],
        )
        tabela.setStyle(TableStyle([
            ('BACKGROUND',     (0, 0),   (-1, 0),    C_LIGHT_BG),
            ('ROWBACKGROUNDS', (0, 1),   (-1, ult - 1), [C_WHITE, C_LIGHT_BG]),
            ('BACKGROUND',     (0, ult), (-1, ult),  C_TOTAL_BG),
            ('SPAN',           (0, ult), (4, ult)),
            ('GRID',           (0, 0),   (-1, -1),   0.4, C_BORDER),
            ('VALIGN',         (0, 0),   (-1, -1),   'MIDDLE'),
            ('LEFTPADDING',    (0, 0),   (-1, -1),   4),
            ('RIGHTPADDING',   (0, 0),   (-1, -1),   4),
            ('TOPPADDING',     (0, 0),   (-1, -1),   3),
            ('BOTTOMPADDING',  (0, 0),   (-1, -1),   3),
        ]))
        el.append(tabela)

    def _rodape(canvas, doc_):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(MARGIN, 8 * mm, f'Emitido em {agora} por {usuario}')
        canvas.drawRightString(doc_.pagesize[0] - MARGIN, 8 * mm, f'Página {doc_.page}')
        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN + 6 * mm,
        title='Relatório de Contas a Pagar', author='Decolog',
    )
    doc.build(el, onFirstPage=_rodape, onLaterPages=_rodape)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="contas_a_pagar_{timezone.localdate():%Y%m%d}.pdf"'
    )
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response