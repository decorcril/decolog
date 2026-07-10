from io import BytesIO
import qrcode

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import KeepTogether, Image as RLImage, HRFlowable

from vendas.models import Pedido, UnidadePedido


def _build_qr_etiqueta(url: str, size_mm: float) -> RLImage:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10, border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return RLImage(buf, width=size_mm * mm, height=size_mm * mm)


@login_required
def etiquetas_pedido(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente').prefetch_related(
            'itens__produto', 'itens__unidades'
        ),
        pk=pk
    )

    # ── Paisagem: 150mm largura x 100mm altura ──
    LARGURA = 150 * mm
    ALTURA  = 100 * mm
    MARGEM  = 6   * mm
    QR_SIZE = 40  * mm

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize=(LARGURA, ALTURA),
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=20 * mm,  bottomMargin=MARGEM,
    )

    conteudo_w = LARGURA - 2 * MARGEM - QR_SIZE - 4 * mm

    # ── Estilos ──
    s_numero  = ParagraphStyle('numero',  fontSize=28, fontName='Helvetica-Bold', leading=17, alignment=TA_LEFT)
    s_cliente = ParagraphStyle('cliente', fontSize=18, fontName='Helvetica',      leading=13, alignment=TA_LEFT, textColor=colors.HexColor('#444444'))
    s_produto = ParagraphStyle('produto', fontSize=18, fontName='Helvetica-Bold', leading=16, alignment=TA_LEFT)
    s_qtd     = ParagraphStyle('qtd',     fontSize=15, fontName='Helvetica',      leading=13, alignment=TA_LEFT, textColor=colors.HexColor('#555555'))
    s_hint    = ParagraphStyle('hint',    fontSize=10,  fontName='Helvetica',      leading=9,  alignment=TA_CENTER, textColor=colors.HexColor('#888888'))

    # ── Coleta unidades ──
    unidades = UnidadePedido.objects.filter(
        item__pedido=pedido
    ).select_related('item__produto').order_by('item__id', 'numero')

    total = unidades.count()

    if total == 0:
        todas = []
        for item in pedido.itens.select_related('produto').all():
            for n in range(item.quantidade):
                todas.append((item.produto.nome, n + 1, item.quantidade, None))
    else:
        todas = [
            (u.item.produto.nome, u.numero, u.item.quantidade, u.token)
            for u in unidades
        ]

    elementos       = []
    total_etiquetas = len(todas)

    for idx, (nome_produto, numero, quantidade_total, token) in enumerate(todas):
        if token:
            url_qr = request.build_absolute_uri(f'/vendas/unidade/{token}/')
        else:
            url_qr = request.build_absolute_uri(f'/vendas/unidade/sem-token/')

        qr_img = _build_qr_etiqueta(url_qr, QR_SIZE / mm)

        lado_esq = [
            Paragraph(f'Pedido {pedido.numero}', s_numero),
            Spacer(1, 8 * mm),
            Paragraph(pedido.cliente.nome, s_cliente),
            Spacer(1, 6 * mm),
            Paragraph(nome_produto, s_produto),
            Spacer(1, 4 * mm),
            Paragraph(f'Unidade {numero} de {quantidade_total}', s_qtd),
        ]

        lado_dir = [
            qr_img,
            Spacer(1, 1 * mm),
            Paragraph('escaneie para\nconfirmar.', s_hint),
        ]

        tabela = Table(
            [[lado_esq, lado_dir]],
            colWidths=[conteudo_w, QR_SIZE + 4 * mm],
        )
        tabela.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',         (1, 0), (1, 0),   'CENTER'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        elementos.append(KeepTogether(tabela))

        if idx < total_etiquetas - 1:
            elementos.append(Spacer(1, 3 * mm))
            elementos.append(HRFlowable(
                width='100%', thickness=0.5,
                color=colors.HexColor('#cccccc'),
                dash=(3, 3),
                spaceBefore=2 * mm, spaceAfter=2 * mm,
            ))

    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="etiquetas_{pedido.numero}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response