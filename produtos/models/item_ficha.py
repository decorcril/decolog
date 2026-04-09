from django.db import models


class ItemFichaTecnica(models.Model):
    ficha = models.ForeignKey(
        'produtos.FichaTecnica',
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Ficha Técnica'
    )
    material = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='usado_em_fichas',
        verbose_name='Material'
    )
    quantidade = models.DecimalField(
        max_digits=10, decimal_places=3,
        verbose_name='Quantidade'
    )
    observacao = models.CharField(
        max_length=200, blank=True, verbose_name='Observação'
    )

    class Meta:
        verbose_name = 'Item da Ficha Técnica'
        verbose_name_plural = 'Itens da Ficha Técnica'
        unique_together = ('ficha', 'material')

    def __str__(self):
        return (
            f'{self.material.nome} — '
            f'{self.quantidade} {self.material.get_unidade_medida_display()}'
        )