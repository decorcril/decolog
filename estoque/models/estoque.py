from django.db import models
from django.core.exceptions import ValidationError


class Estoque(models.Model):
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='estoques',
        verbose_name='Produto'
    )
    local = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='estoques',
        verbose_name='Local'
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=3,
        default=0, verbose_name='Quantidade'
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    estoque_minimo = models.DecimalField(
    max_digits=10, decimal_places=0,
    default=0, verbose_name='Estoque Mínimo'
    )

    class Meta:
        verbose_name = 'Estoque'
        verbose_name_plural = 'Estoques'
        unique_together = ('produto', 'local')
        ordering = ['local__nome', 'produto__nome']

    def __str__(self):
        return f'{self.produto.nome} — {self.local.nome}: {self.quantidade}'

    def adicionar(self, qtd):
        if qtd <= 0:
            raise ValueError('Quantidade deve ser positiva.')
        self.quantidade += qtd
        self.save(update_fields=['quantidade', 'atualizado_em'])

    def subtrair(self, qtd):
        if qtd <= 0:
            raise ValueError('Quantidade deve ser positiva.')
        if self.quantidade - qtd < 0:
            raise ValidationError(
                f'Estoque insuficiente. Disponível: {self.quantidade}. Solicitado: {qtd}.'
            )
        self.quantidade -= qtd
        self.save(update_fields=['quantidade', 'atualizado_em'])

    @classmethod
    def get_or_create_saldo(cls, produto, local):
        obj, _ = cls.objects.get_or_create(produto=produto, local=local)
        return obj
    
    @property
    def estoque_baixo(self):
        return self.estoque_minimo > 0 and self.quantidade <= self.estoque_minimo
    
    @property
    def status_estoque(self):
        if self.estoque_minimo == 0:
            return 'sem_minimo'
        if self.quantidade <= self.estoque_minimo:
            return 'critico'
        if self.quantidade <= self.estoque_minimo * 2:
            return 'alerta'
        return 'estavel'

    @property
    def status_display(self):
        labels = {
            'sem_minimo': '',
            'critico': 'Crítico',
            'alerta': 'Repor em breve',
            'estavel': 'Estável',
        }
        return labels.get(self.status_estoque, '')