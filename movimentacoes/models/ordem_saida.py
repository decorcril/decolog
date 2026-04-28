from django.db import models
from django.contrib.auth.models import User
from django.db import transaction


class OrdemSaida(models.Model):

    MOTIVO_CHOICES = [
        ('venda', 'Venda'),
        ('perda', 'Perda / Avaria'),
        ('uso_interno', 'Uso Interno'),
        ('troca', 'Troca'),
        ('reposicao', 'Reposição'),
        ('publicidade', 'Publicidade'),
        ('manutencao', 'Manutenção'),
        ('outro', 'Outro'),
    ]

    numero = models.CharField(
        max_length=20, unique=True,
        verbose_name='Número da Ordem'
    )
    local_origem = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='ordens_saida_lote',
        verbose_name='Local de Origem'
    )
    motivo = models.CharField(
        max_length=20, choices=MOTIVO_CHOICES,
        default='venda', verbose_name='Motivo'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ordens_saida_criadas',
        verbose_name='Criado por'
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')

    class Meta:
        verbose_name = 'Ordem de Saída'
        verbose_name_plural = 'Ordens de Saída'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'OS-{self.numero} | {self.local_origem} | {self.get_motivo_display()}'

    @classmethod
    def gerar_numero(cls):
        from django.utils import timezone
        prefixo = timezone.now().strftime('%Y%m')
        ultima = cls.objects.filter(numero__startswith=prefixo).order_by('-numero').first()
        if ultima:
            seq = int(ultima.numero[-4:]) + 1
        else:
            seq = 1
        return f'{prefixo}{seq:04d}'

    @transaction.atomic
    def aplicar(self, usuario):
        from movimentacoes.models import Movimentacao
        for item in self.itens.all():
            Movimentacao.objects.create(
                produto=item.produto,
                local=self.local_origem,
                tipo='saida',
                motivo=self.motivo,
                quantidade=item.quantidade,
                observacao=self.observacao,
                usuario=usuario,
            )


class ItemOrdemSaida(models.Model):
    ordem = models.ForeignKey(
        OrdemSaida,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Ordem'
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        verbose_name='Produto'
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Quantidade'
    )

    class Meta:
        verbose_name = 'Item da Ordem de Saída'
        verbose_name_plural = 'Itens da Ordem de Saída'

    def __str__(self):
        return f'{self.produto.nome} — {self.quantidade}'