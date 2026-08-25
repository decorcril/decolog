from django.db import models


class FichaTecnica(models.Model):
    produto = models.OneToOneField(
        'produtos.Produto',
        on_delete=models.CASCADE,
        related_name='ficha_tecnica',
        verbose_name='Produto Final'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    permite_personalizacao = models.BooleanField(
        default=False,
        verbose_name='Permite Personalização',
        help_text='Se ativo, as quantidades podem ser ajustadas por ordem de produção'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ficha Técnica'
        verbose_name_plural = 'Fichas Técnicas'

    def __str__(self):
        return f'Ficha Técnica — {self.produto.nome}'

    @property
    def is_kit(self):
        """
        True se todos os componentes desta ficha são produto_final — ou
        seja, ela representa um Kit (conjunto de peças prontas que se
        vendem juntas, ex: Trio = P + M + G), e não uma receita de
        produção (componentes insumo/chapa consumidos como matéria-prima).

        Precisa de pelo menos 1 item — ficha vazia não é Kit.
        """
        itens = list(self.itens.select_related('material').all())
        return bool(itens) and all(
            item.material.categoria == 'produto_final' for item in itens
        )