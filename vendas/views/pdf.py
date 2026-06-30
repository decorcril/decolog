from io import BytesIO
from datetime import datetime
import os
import zoneinfo

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether,
)
from reportlab.platypus import Image as RLImage
import qrcode

from core.mixins import acesso_vendas
from vendas.models import Pedido


# ── PALETA ───────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor('#2C2C2C')
C_LIGHT_BG   = colors.HexColor('#F2F2F2')
C_BORDER     = colors.HexColor('#CBD5E1')
C_TEXT_MUTED = colors.HexColor('#64748B')
C_WHITE      = colors.white
C_TOTAL_BG   = colors.HexColor('#E8E8E8')

PAGE_W, PAGE_H = A4
MARGIN         = 6 * mm
CONTENT_W      = PAGE_W - 2 * MARGIN


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _fmt_brl(value) -> str:
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _build_qr(url: str, size_mm: float) -> RLImage:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10, border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=size_mm * mm, height=size_mm * mm)


def _build_address(cliente) -> str:
    parts = []
    street = ''
    if cliente.logradouro:
        street = cliente.logradouro
        if cliente.numero: street += f', {cliente.numero}'
        if cliente.complemento: street += f' - {cliente.complemento}'
    if street: parts.append(street)
    if cliente.bairro: parts.append(cliente.bairro)
    if cliente.cidade:
        cidade = cliente.cidade
        if cliente.estado: cidade += f'/{cliente.estado}'
        parts.append(cidade)
    if cliente.cep: parts.append(f'CEP {cliente.cep}')
    return ' - '.join(parts) if parts else '—'


def _build_payments_text(pedido) -> str:
    pagamentos = pedido.pagamentos.all()
    if not pagamentos.exists():
        return '—'
    lines = []
    for p in pagamentos:
        line = f'{p.get_metodo_display()}   {_fmt_brl(p.valor)}'
        if p.transacao:
            line += f'   |   Nº Transação: {p.transacao}'
        lines.append(line)
    return '<br/>'.join(lines)


def _styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        'company':     s('company',     fontSize=18,  textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=22),
        'company_sub': s('company_sub', fontSize=9,   textColor=C_PRIMARY, fontName='Helvetica',      leading=13),
        'doc_number':  s('doc_number',  fontSize=20,  textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=24, alignment=TA_RIGHT),
        'doc_label':   s('doc_label',   fontSize=9,   textColor=C_PRIMARY, fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'section':     s('section',     fontSize=10,  textColor=C_PRIMARY, fontName='Helvetica-Bold', spaceBefore=2, spaceAfter=4, leading=12),
        'label':       ParagraphStyle('label', fontSize=10, textColor=colors.black, fontName='Helvetica-Bold', leading=11),
        'value':       ParagraphStyle('value', fontSize=9,  textColor=colors.black, fontName='Helvetica', leading=13),
        'th':          s('th',   fontSize=9, textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=12),
        'th_c':        ParagraphStyle('th_c', fontSize=9, textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=12, alignment=TA_CENTER),
        'td':          ParagraphStyle('td',   fontSize=9.5, textColor=colors.black, fontName='Helvetica', leading=13),
        'td_c':        ParagraphStyle('td_c', fontSize=9.5, textColor=colors.black, fontName='Helvetica', leading=13, alignment=TA_CENTER),
        'td_r':        ParagraphStyle('td_r', fontSize=9.5, textColor=colors.black, fontName='Helvetica', leading=13, alignment=TA_RIGHT),
        'td_r_bold':   ParagraphStyle('td_r_bold', fontSize=9.5, textColor=colors.black, fontName='Helvetica-Bold', leading=13, alignment=TA_RIGHT),
        'total_label': s('total_label', fontSize=9, textColor=colors.black, fontName='Helvetica', leading=13, alignment=TA_RIGHT),
        'total_value': s('total_value', fontSize=9, textColor=colors.black, fontName='Helvetica-Bold', leading=13, alignment=TA_LEFT),
        'grand_label': s('grand_label', fontSize=11, textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=15, alignment=TA_RIGHT),
        'grand_value': s('grand_value', fontSize=11, textColor=C_PRIMARY, fontName='Helvetica-Bold', leading=15, alignment=TA_LEFT),
        'obs':         s('obs', fontSize=8.5, textColor=colors.black, fontName='Helvetica', leading=13),
        'qr_hint':     s('qr_hint', fontSize=6.5, textColor=C_TEXT_MUTED, fontName='Helvetica', leading=9, alignment=TA_CENTER),
    }


def _section_title(text: str, s: dict) -> Paragraph:
    return Paragraph(text.upper(), s['section'])


def _info_grid(rows: list, col_widths: list, s: dict) -> Table:
    table_rows = []
    for row_pair in rows:
        # Filtra pares onde label e valor estão vazios
        pares_validos = [(label, value) for label, value in row_pair if label and value]

        if not pares_validos:
            continue

        cells = []
        for label, value in pares_validos:
            cells.append(Paragraph(label, s['label']))
            cells.append(Paragraph(str(value), s['value']))

        # Preenche células vazias se a linha ficou com só 1 par (mantém o layout)
        while len(cells) < len(col_widths):
            cells.append(Paragraph('', s['label']))

        table_rows.append(cells)

    if not table_rows:
        return Table([['']], colWidths=[sum(col_widths)])

    t = Table(table_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#000')),
        *[('BACKGROUND', (0, i), (-1, i), C_LIGHT_BG) for i in range(0, len(table_rows), 2)],
    ]))
    return t

def _full_width_row(label: str, value: str, col_lbl: float, content_w: float, s: dict, bg=None) -> Table:
    t = Table(
        [[Paragraph(label, s['label']), Paragraph(value, s['value'])]],
        colWidths=[col_lbl, content_w - col_lbl],
    )
    style = [
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.HexColor('#000')),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, colors.HexColor('#000')),
    ]
    if bg:
        style.append(('BACKGROUND', (0, 0), (-1, -1), bg))
    t.setStyle(TableStyle(style))
    return t


def _build_compact_qr(pedido, request, qr_width: float, s: dict) -> Table:
    url    = request.build_absolute_uri(f'/vendas/expedir/{pedido.token_expedicao}/')
    qr_img = _build_qr(url, size_mm=22)

    inner = Table(
        [[qr_img], [Paragraph('escaneie para confirmar envio', s['qr_hint'])]],
        colWidths=[qr_width],
    )
    inner.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 1), (0, 1),   2),
    ]))
    return inner


def _build_items_table(pedido, content_w: float, s: dict) -> list:
    def _th(text): return Paragraph(text, s['th'])
    def _th_c(text): return Paragraph(text, s['th_c'])
    def _td(text): return Paragraph(str(text), s['td'])
    def _td_c(text): return Paragraph(str(text), s['td_c'])
    def _td_r(text, bold=False): return Paragraph(str(text), s['td_r_bold'] if bold else s['td_r'])

    COL_QTD   = 16 * mm
    COL_PRICE = 28 * mm
    COL_TOTAL = 28 * mm
    COL_DESC  = content_w - COL_QTD - COL_PRICE - COL_TOTAL

    header_row = [_th_c('Qtd'), _th('Produto'), _th_c('Vlr. Unit.'), _th_c('Total')]
    col_widths = [COL_QTD, COL_DESC, COL_PRICE, COL_TOTAL]

    rows = [header_row]
    for item in pedido.itens.select_related('produto').all():
        rows.append([
            _td_c(item.quantidade),
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
        ('ALIGN',          (0, 0), (0, -1),  'CENTER'),
        ('ALIGN',          (2, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING',    (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 4),
        ('TOPPADDING',     (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 1), (-1, -1), 5),
    ]))
    return [t]


def _build_totals_table(pedido, content_w: float, s: dict) -> Table:
    COL_SPACER = content_w * 0.4
    COL_LBL    = content_w * 0.35
    COL_VAL    = content_w * 0.25

    rows = []
    if pedido.total_desconto > 0:
        rows.append(('Total Bruto:', _fmt_brl(pedido.total_produtos), False))
        rows.append(('(-) Desconto:', _fmt_brl(pedido.total_desconto), False))

    rows += [
        ('Total Produtos:', _fmt_brl(pedido.total_produtos - pedido.total_desconto), False),
        ('(+) Frete:',      _fmt_brl(pedido.frete),                                  False),
        ('Total Geral:',    _fmt_brl(pedido.total_geral),                            True),
        ('Total Pago:',     _fmt_brl(pedido.total_pago),                             False),
        ('Saldo a Pagar:',  _fmt_brl(pedido.saldo_restante),                         False),
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


# ══════════════════════════════════════════════════════════════
# VIEW PRINCIPAL
# ══════════════════════════════════════════════════════════════

@acesso_vendas
def pedido_pdf(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente', 'criado_por'),
        pk=pk
    )
    cliente = pedido.cliente
    s       = _styles()
    now     = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime('%d/%m/%Y  %H:%M')

    col_lbl = 30 * mm
    col_val = CONTENT_W / 2 - col_lbl
    cw      = [col_lbl, col_val, col_lbl, col_val]

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f"Pedido #{pedido.numero}", author='Decorcril',
    )

    el = []

    # ── Cabeçalho ──
    left_col = [
        Paragraph("DECORCRIL", s['company']),
        Spacer(1, 2 * mm),
        Paragraph("Decorcril Acrílicos e Artesanatos Ltda.", s['company_sub']),
        Paragraph("Rua Prudente de Moraes, 1327 — Suzano/SP", s['company_sub']),
        Paragraph("CNPJ: 45.401.044/0001-61", s['company_sub']),
    ]
    right_col = [
        Paragraph("PEDIDO DE VENDA",     s['doc_label']),
        Paragraph(f"Nº {pedido.numero}", s['doc_number']),
        Spacer(1, 2 * mm),
        Paragraph(f"Emissão: {now}",     s['doc_label']),
    ]
    header = Table(
        [[left_col, right_col]],
        colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45],
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
        [('Cliente',    cliente.nome),
         ('Pedido Nº',  pedido.numero)],
        [('CNPJ / CPF', cliente.documento),
         ('Data',       pedido.criado_em.strftime('%d/%m/%Y'))],
        [('Telefone',   cliente.telefone or '—'),
         ('WhatsApp',   cliente.whatsapp or '—')],
        [('Contato',    pedido.contato )],
    ], cw, s))
    el.append(_full_width_row('Endereço', _build_address(cliente), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Dados Comerciais ──
    el.append(_section_title('Dados Comerciais', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Vendedor',       pedido.criado_por.get_full_name() or pedido.criado_por.username),
         ('Tipo de Venda',  pedido.get_tipo_venda_display() if pedido.tipo_venda else None)],
        [('Transportadora', pedido.transportadora),
         ('Pagamento',      pedido.condicao_pagamento)],
    ], cw, s))
    if pedido.pagamentos.exists():
        el.append(_full_width_row('Pagamentos', _build_payments_text(pedido), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Itens ──
    el.append(_section_title('Itens do Pedido', s))
    el.append(Spacer(1, 2 * mm))
    el += _build_items_table(pedido, CONTENT_W, s)
    el.append(Spacer(1, 4 * mm))

    # ── Observações ──
    if pedido.observacoes:
        el.append(_section_title('Observações', s))
        el.append(Spacer(1, 2 * mm))
        obs = Table([[Paragraph(pedido.observacoes, s['obs'])]], colWidths=[CONTENT_W])
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

    # ── Resumo Financeiro + QR Code ──
    el.append(_section_title('Resumo Financeiro', s))
    el.append(Spacer(1, 2 * mm))

    qr_width     = 35 * mm
    totals_width = CONTENT_W - qr_width - 5 * mm

    side_by_side = Table(
        [[_build_compact_qr(pedido, request, qr_width, s), _build_totals_table(pedido, totals_width, s)]],
        colWidths=[qr_width, totals_width],
    )
    side_by_side.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(KeepTogether(side_by_side))

    doc.build(el)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pedido_{pedido.numero}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response