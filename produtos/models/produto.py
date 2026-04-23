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

    def estoque_total(self):
        from estoque.models import Estoque
        result = Estoque.objects.filter(produto=self).aggregate(
            total=models.Sum('quantidade')
        )
        return result['total'] or 0