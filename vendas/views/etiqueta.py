from io import BytesIO
import qrcode
import base64

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.platypus import KeepTogether

from vendas.models import Pedido


def _build_qr_etiqueta(url: str, size_mm: float) -> RLImage:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8, border=1,
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
        Pedido.objects.select_related('cliente').prefetch_related('itens__produto'),
        pk=pk
    )

    # ── Configurações da etiqueta ──
    LARGURA  = 100 * mm
    ALTURA   = 70  * mm
    MARGEM   = 4   * mm
    QR_SIZE  = 22  * mm

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize=(LARGURA, ALTURA),
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM,  bottomMargin=MARGEM,
    )

    # ── Estilos ──
    s_numero  = ParagraphStyle('numero',  fontSize=9,  fontName='Helvetica-Bold', leading=11, alignment=TA_LEFT)
    s_cliente = ParagraphStyle('cliente', fontSize=8,  fontName='Helvetica',      leading=10, alignment=TA_LEFT)
    s_produto = ParagraphStyle('produto', fontSize=11, fontName='Helvetica-Bold', leading=13, alignment=TA_LEFT)
    s_qtd     = ParagraphStyle('qtd',     fontSize=8,  fontName='Helvetica',      leading=10, alignment=TA_LEFT, textColor=colors.HexColor('#555555'))
    s_hint    = ParagraphStyle('hint',    fontSize=6,  fontName='Helvetica',      leading=8,  alignment=TA_CENTER, textColor=colors.HexColor('#888888'))

    url_qr = request.build_absolute_uri(f'/vendas/separar/{pedido.token_separacao}/')

    # ── Gera uma etiqueta por item do pedido ──
    # ── Gera uma etiqueta por unidade de cada item ──
    elementos = []
    total_etiquetas = sum(item.quantidade for item in pedido.itens.select_related('produto').all())
    contador = 0

    for item in pedido.itens.select_related('produto').all():
        for unidade in range(item.quantidade):
            qr_img = _build_qr_etiqueta(url_qr, QR_SIZE / mm)

            conteudo_w = LARGURA - 2 * MARGEM - QR_SIZE - 3 * mm

            lado_esq = [
                Paragraph(f'Pedido {pedido.numero}', s_numero),
                Spacer(1, 1 * mm),
                Paragraph(pedido.cliente.nome, s_cliente),
                Spacer(1, 3 * mm),
                Paragraph(item.produto.nome, s_produto),
                Spacer(1, 1 * mm),
                Paragraph(f'Unidade {unidade + 1} de {item.quantidade}', s_qtd),
            ]

            lado_dir = [
                qr_img,
                Paragraph('escaneie para\nconfirmar separação', s_hint),
            ]

            tabela = Table(
                [[lado_esq, lado_dir]],
                colWidths=[conteudo_w, QR_SIZE + 3 * mm],
            )
            tabela.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

            elementos.append(KeepTogether(tabela))
            contador += 1

            # Separador entre etiquetas (exceto última)
            if contador < total_etiquetas:
                elementos.append(Spacer(1, 2 * mm))
                from reportlab.platypus import HRFlowable
                elementos.append(HRFlowable(
                    width='100%', thickness=0.5,
                    color=colors.HexColor('#cccccc'),
                    dash=(2, 2),
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