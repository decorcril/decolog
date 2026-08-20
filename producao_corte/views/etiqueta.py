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

from producao_corte.models import RegistroCorte, ProdutoCortado


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
def etiquetas_registro_corte(request, pk):
    registro = get_object_or_404(RegistroCorte, pk=pk)
    pecas    = ProdutoCortado.objects.filter(
        item_corte__registro=registro
    ).select_related('produto').order_by('produto__nome')

    LARGURA = 150 * mm
    ALTURA  = 100 * mm
    MARGEM  = 5   * mm
    QR_SIZE = 38  * mm

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize=(LARGURA, ALTURA),
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=6 * mm,  bottomMargin=MARGEM,
    )

    conteudo_w = LARGURA - 2 * MARGEM - QR_SIZE - 4 * mm

    s_codigo  = ParagraphStyle('codigo',  fontSize=30,  fontName='Helvetica', leading=15, alignment=TA_LEFT, textColor=colors.HexColor('#666666'))
    s_produto = ParagraphStyle('produto', fontSize=23, fontName='Helvetica-Bold', leading=24, alignment=TA_LEFT)
    s_obs     = ParagraphStyle('obs',     fontSize=16,  fontName='Helvetica-Bold', leading=17, alignment=TA_LEFT, textColor=colors.HexColor('#444444'))
    s_hint    = ParagraphStyle('hint',    fontSize=10, fontName='Helvetica',      leading=8,  alignment=TA_CENTER, textColor=colors.HexColor('#888888'))

    elementos   = []
    total_pecas = pecas.count()

    for idx, peca in enumerate(pecas):
        url_qr = request.build_absolute_uri(f'/montagem/peca/{peca.token}/')
        qr_img = _build_qr_etiqueta(url_qr, QR_SIZE / mm)

        obs = peca.produto.descricao or ''

        # ── Bloco 1: código, bem no topo, largura inteira ──
        bloco = [Paragraph(peca.produto.codigo or '', s_codigo)]

        # ── Bloco 2: nome do produto (esquerda) + QR (direita) ──
        lado_esq = [Paragraph(peca.produto.nome, s_produto)]
        lado_dir = [
            qr_img,
            Paragraph('escaneie para registrar.', s_hint),
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

        bloco += [Spacer(1, 6 * mm), tabela]

        # ── Bloco 3: observação, embaixo, largura inteira ──
        if obs:
            bloco += [
                Spacer(1, 6 * mm),
                Paragraph(obs, s_obs),
            ]

        elementos.append(KeepTogether(bloco))

        if idx < total_pecas - 1:
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
    response['Content-Disposition'] = f'inline; filename="etiquetas_corte_{registro.pk}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response