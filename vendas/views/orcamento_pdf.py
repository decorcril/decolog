from io import BytesIO
from datetime import datetime
from functools import partial
import os
import zoneinfo

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)

from core.mixins import acesso_vendas
from vendas.models.orcamento import Orcamento
from vendas.views.pdf import (
    C_PRIMARY, C_LIGHT_BG, C_BORDER, C_WHITE, C_TOTAL_BG,
    PAGE_W, PAGE_H, MARGIN, CONTENT_W, LOGO_PATH,
    _fmt_brl, _build_address, _styles, _section_title,
    _info_grid, _full_width_row,
)


def _draw_footer_logo(canvas, doc):
    """Desenha só o logo/mascote, fixo no canto inferior direito da página
    — mesma posição e tamanho do PDF de pedido, sem o QR code."""
    canvas.saveState()

    if os.path.exists(LOGO_PATH):
        logo_size = 31 * mm
        logo_x    = PAGE_W - MARGIN - logo_size
        logo_y    = MARGIN - 2 * mm

        canvas.drawImage(
            LOGO_PATH, logo_x, logo_y,
            width=logo_size, height=logo_size,
            preserveAspectRatio=True, mask='auto',
        )

    canvas.restoreState()


def _build_items_table_orcamento(orcamento, content_w: float, s: dict) -> list:
    def _th(text): return Paragraph(text, s['th'])
    def _th_c(text): return Paragraph(text, s['th_c'])
    def _td(text): return Paragraph(str(text), s['td'])
    def _td_c(text): return Paragraph(str(text), s['td_c'])
    def _td_r(text, bold=False): return Paragraph(str(text), s['td_r_bold'] if bold else s['td_r'])

    COL_QTD    = 14 * mm
    COL_CODIGO = 22 * mm
    COL_PRICE  = 28 * mm
    COL_TOTAL  = 28 * mm
    COL_DESC   = content_w - COL_QTD - COL_CODIGO - COL_PRICE - COL_TOTAL

    header_row = [_th_c('Qtd'), _th_c('Código'), _th('Produto'), _th_c('Vlr. Unit.'), _th_c('Total')]
    col_widths = [COL_QTD, COL_CODIGO, COL_DESC, COL_PRICE, COL_TOTAL]

    rows = [header_row]
    for item in orcamento.itens.select_related('produto').all():
        rows.append([
            _td_c(item.quantidade),
            _td_c(item.produto.codigo or '—'),
            _td(item.produto.nome),
            _td_r(_fmt_brl(item.preco_unitario)),
            _td_r(_fmt_brl(item.subtotal), bold=True),
        ])

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  C_LIGHT_BG),
        ('TOPPADDING',     (0, 0), (-1, 0),  5),
        ('BOTTOMPADDING',  (0, 0), (-1, 0),  5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_LIGHT_BG]),
        ('GRID',           (0, 0), (-1, -1), 0.8, colors.HexColor('#000')),
        ('VALIGN',         (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',          (0, 0), (1, -1),  'CENTER'),
        ('ALIGN',          (3, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING',    (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 4),
        ('TOPPADDING',     (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 1), (-1, -1), 5),
    ]))
    return [t]


def _build_totals_table_orcamento(orcamento, content_w: float, s: dict) -> Table:
    COL_SPACER = content_w * 0.4
    COL_LBL    = content_w * 0.35
    COL_VAL    = content_w * 0.25

    rows = []
    if orcamento.total_desconto > 0:
        rows.append(('Total Bruto:', _fmt_brl(orcamento.total_produtos), False))
        rows.append(('(-) Desconto:', _fmt_brl(orcamento.total_desconto), False))

    rows += [
        ('Total Produtos:', _fmt_brl(orcamento.total_produtos - orcamento.total_desconto), False),
        ('(+) Frete:',      _fmt_brl(orcamento.frete),                                     False),
        ('Total Geral:',    _fmt_brl(orcamento.total_geral),                               True),
    ]
    grand_idx = next(i for i, r in enumerate(rows) if r[2])

    data = [
        [
            Paragraph('', s['total_label']),
            Paragraph(label, s['grand_label'] if grand else s['total_label']),
            Paragraph(value, s['grand_value'] if grand else s['total_value']),
        ]
        for label, value, grand in rows
    ]

    t = Table(data, colWidths=[COL_SPACER, COL_LBL, COL_VAL])
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0),           (-1, -1),           'MIDDLE'),
        ('TOPPADDING',    (0, 0),           (-1, -1),           2),
        ('BOTTOMPADDING', (0, 0),           (-1, -1),           2),
        ('RIGHTPADDING',  (1, 0),           (1, -1),            2),
        ('GRID',          (1, 0),           (-1, -1),           0.5, colors.HexColor('#000')),
        ('BACKGROUND',    (1, grand_idx),   (2, grand_idx),     C_TOTAL_BG),
        ('LINEABOVE',     (1, grand_idx),   (2, grand_idx),     0.7, C_PRIMARY),
        ('LINEBELOW',     (1, grand_idx),   (2, grand_idx),     0.7, C_PRIMARY),
        ('TOPPADDING',    (0, grand_idx),   (-1, grand_idx),    4),
        ('BOTTOMPADDING', (0, grand_idx),   (-1, grand_idx),    4),
        ('LINEABOVE',     (1, len(rows)-1), (2, len(rows)-1),   0.4, C_BORDER),
    ]))
    return t


@acesso_vendas
def orcamento_pdf(request, pk):
    orcamento = get_object_or_404(
        Orcamento.objects.select_related('cliente', 'criado_por'),
        pk=pk
    )
    cliente = orcamento.cliente
    s       = _styles()
    now     = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime('%d/%m/%Y  %H:%M')

    col_lbl = 30 * mm
    col_val = CONTENT_W / 2 - col_lbl
    cw      = [col_lbl, col_val, col_lbl, col_val]

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN + 30 * mm,  # reserva espaço pro logo fixo no rodapé
        title=f"Orçamento #{orcamento.numero}", author='Decorcril',
    )

    el = []

    # ── Cabeçalho ──
    left_col = [
        Paragraph("DECORCRIL", s['company']),
        Spacer(1, 2 * mm),
        Paragraph("Decorcril Acrílicos e Artesanatos Ltda.", s['company_sub']),
        Paragraph("Endereço: Rua Prudente de Moraes, 1327 — Suzano/SP, 08610-005 ", s['company_sub']),
        Paragraph("CNPJ: 45.401.044/0001-61", s['company_sub']),
        Paragraph("WhatsApp (11) 97899-9091", s['company_sub']),
    ]
    right_col = [
        Paragraph("ORÇAMENTO",              s['doc_label']),
        Paragraph(f"Nº {orcamento.numero}", s['doc_number']),
        Spacer(1, 2 * mm),
        Paragraph(f"Emissão: {now}",        s['doc_label']),
    ]
    header = Table(
        [[left_col, right_col]],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35],
        rowHeights=[30 * mm],
    )
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm),
    ]))
    el.append(header)
    el.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceBefore=3*mm, spaceAfter=4*mm))

    # ── Dados do Cliente ──
    el.append(_section_title('Dados do Cliente', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Cliente',      cliente.nome),
         ('Orçamento Nº', orcamento.numero)],
        [('CNPJ / CPF',   cliente.documento),
         ('Data',         orcamento.criado_em.strftime('%d/%m/%Y'))],
        [('Telefone',     cliente.telefone or '—'),
         ('WhatsApp',     cliente.whatsapp or '—')],
        [('Email',        cliente.email or '—'),
         ('Responsável',  orcamento.contato or '—')],
    ], cw, s))
    el.append(_full_width_row('Endereço', _build_address(cliente), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Dados Comerciais ──
    el.append(_section_title('Dados Comerciais', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Vendedor',           orcamento.criado_por.get_full_name() or orcamento.criado_por.username),
         ('Tipo de Venda',      orcamento.get_tipo_venda_display() if orcamento.tipo_venda else None)],
        [('Transportadora',     orcamento.transportadora),
         ('Pagamento',          orcamento.condicao_pagamento)],
        [('Prazo de Confecção', orcamento.get_prazo_confeccao_display() if orcamento.prazo_confeccao else None),
         ('Válido até',         orcamento.validade.strftime('%d/%m/%Y') if orcamento.validade else None)],
    ], cw, s))
    el.append(Spacer(1, 4 * mm))

    # ── Itens ──
    el.append(_section_title('Itens do Orçamento', s))
    el.append(Spacer(1, 2 * mm))
    el += _build_items_table_orcamento(orcamento, CONTENT_W, s)
    el.append(Spacer(1, 4 * mm))

    # ── Observações ──
    if orcamento.observacoes:
        el.append(_section_title('Observações', s))
        el.append(Spacer(1, 2 * mm))
        obs = Table([[Paragraph(orcamento.observacoes, s['obs'])]], colWidths=[CONTENT_W])
        obs.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), C_LIGHT_BG),
            ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5 * mm),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5 * mm),
            ('TOPPADDING',    (0, 0), (-1, -1), 4 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
        ]))
        el.append(obs)
        el.append(Spacer(1, 4 * mm))

    # ── Resumo Financeiro ──
    el.append(_section_title('Resumo Financeiro', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_build_totals_table_orcamento(orcamento, CONTENT_W, s))

    doc.build(el, onFirstPage=_draw_footer_logo, onLaterPages=_draw_footer_logo)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="orcamento_{orcamento.numero}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response