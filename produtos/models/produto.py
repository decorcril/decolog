from django.db import models


class Produto(models.Model):
    CATEGORIA_INSUMO = 'insumo'
    CATEGORIA_CHAPA = 'chapa'
    CATEGORIA_FINAL = 'produto_final'

    CATEGORIA_CHOICES = [
        (CATEGORIA_INSUMO, 'Insumo'),
        (CATEGORIA_CHAPA, 'Chapa de Acrílico'),
        (CATEGORIA_FINAL, 'Produto Final'),
    ]

    UNIDADE_CHOICES = [
        ('un', 'Unidade'),
        ('kg', 'Quilograma'),
        ('g', 'Grama'),
        ('m', 'Metro'),
        ('m2', 'Metro Quadrado'),
        ('cm', 'Centímetro'),
        ('l', 'Litro'),
        ('ml', 'Mililitro'),
        ('cx', 'Caixa'),
        ('pct', 'Pacote'),
        ('chp', 'Chapa'),
        ('rolo', 'Rolo'),
        ('tubo', 'Tubo'),
    ]

    COR_CHOICES = [
        ('cristal', 'Cristal'),
        ('branco', 'Branco'),
        ('preto', 'Preto'),
        ('vermelho', 'Vermelho'),
        ('azul_bebe', 'Azul Bebê'),
        ('amarelo', 'Amarelo'),
        ('rosa_bebe', 'Rosa Bebê'),
        ('espelhado', 'Espelhado'),
        ('outro', 'Outro (especificar cor nas observações)'),
    ]

    # Dados básicos
    codigo = models.CharField(
        max_length=50, blank=True, unique=True,
        null=True, verbose_name='Código'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome')
    categoria = models.CharField(
        max_length=20, choices=CATEGORIA_CHOICES,
        verbose_name='Categoria'
    )
    unidade_medida = models.CharField(
        max_length=5, choices=UNIDADE_CHOICES,
        default='un', verbose_name='Unidade de Medida'
    )
    estoque_minimo = models.DecimalField(
        max_digits=10, decimal_places=3,
        default=0, verbose_name='Estoque Mínimo'
    )

    # Cor e espessura (chapas e produtos derivados)
    cor = models.CharField(
        max_length=20, choices=COR_CHOICES,
        blank=True, verbose_name='Cor'
    )
    espessura_mm = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True, verbose_name='Espessura (mm)'
    )

    # Dimensões chapas (em mm)
    largura_mm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Largura (mm)'
    )
    comprimento_mm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Comprimento (mm)'
    )

    # Dimensões outros produtos (em cm)
    largura_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Largura (cm)'
    )
    comprimento_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Comprimento (cm)'
    )
    altura_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Altura (cm)'
    )
    diametro_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Diâmetro (cm)'
    )
    profundidade_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Profundidade (cm)'
    )
    curvatura_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name='Curvatura (cm)'
    )

    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.get_categoria_display()})'

    @property
    def is_insumo(self):
        return self.categoria == self.CATEGORIA_INSUMO

    @property
    def is_chapa(self):
        return self.categoria == self.CATEGORIA_CHAPA

    @property
    def is_produto_final(self):
        return self.categoria == self.CATEGORIA_FINAL

    @property
    def is_materia_prima(self):
        return self.categoria in (self.CATEGORIA_INSUMO, self.CATEGORIA_CHAPA)

    def dimensoes_display(self):
        def fmt(v):
            if v is None:
                return None
            return int(v) if v == int(v) else v

        if self.is_chapa:
            parts = []
            if self.largura_mm and self.comprimento_mm:
                parts.append(f'{fmt(self.largura_mm)}x{fmt(self.comprimento_mm)}mm')
            elif self.largura_mm:
                parts.append(f'L: {fmt(self.largura_mm)}mm')
            elif self.comprimento_mm:
                parts.append(f'C: {fmt(self.comprimento_mm)}mm')
            if self.espessura_mm:
                parts.append(f'Esp: {fmt(self.espessura_mm)}mm')
            return ' · '.join(parts) if parts else ''

        dims = []
        if self.largura_cm and self.comprimento_cm and self.altura_cm:
            dims.append(f'{fmt(self.largura_cm)}x{fmt(self.comprimento_cm)}x{fmt(self.altura_cm)}cm')
        elif self.largura_cm and self.comprimento_cm:
            dims.append(f'{fmt(self.largura_cm)}x{fmt(self.comprimento_cm)}cm')
        elif self.largura_cm:
            dims.append(f'L: {fmt(self.largura_cm)}cm')
        elif self.comprimento_cm:
            dims.append(f'C: {fmt(self.comprimento_cm)}cm')
        elif self.altura_cm:
            dims.append(f'A: {fmt(self.altura_cm)}cm')
        if self.diametro_cm:
            dims.append(f'Ø: {fmt(self.diametro_cm)}cm')
        if self.profundidade_cm:
            dims.append(f'P: {fmt(self.profundidade_cm)}cm')
        if self.curvatura_cm:
            dims.append(f'Curv: {fmt(self.curvatura_cm)}cm')
        if self.espessura_mm:
            dims.append(f'Esp: {fmt(self.espessura_mm)}mm')
        return ' · '.join(dims) if dims else ''

    def estoque_total(self):
        from estoque.models import Estoque
        result = Estoque.objects.filter(produto=self).aggregate(
            total=models.Sum('quantidade')
        )
        return result['total'] or 0

    def estoque_baixo(self):
        return self.estoque_minimo > 0 and self.estoque_total() <= self.estoque_minimo