from django.db import models
from django.contrib.auth.models import User
from django.db import transaction


class OrdemTransferencia(models.Model):

    STATUS_TRANSITO = 'em_transito'
    STATUS_RECEBIDO = 'recebido'
    STATUS_CANCELADO = 'cancelado'

    STATUS_CHOICES = [
        (STATUS_TRANSITO, 'Em Trânsito'),
        (STATUS_RECEBIDO, 'Recebido'),
        (STATUS_CANCELADO, 'Cancelado'),
    ]

    numero = models.CharField(
        max_length=20, unique=True,
        verbose_name='Número da Ordem'
    )
    local_origem = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='ordens_saida',
        verbose_name='Local de Origem'
    )
    local_destino = models.ForeignKey(
        'core.Local',
        on_delete=models.PROTECT,
        related_name='ordens_entrada',
        verbose_name='Local de Destino'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_TRANSITO,
        verbose_name='Status'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ordens_criadas',
        verbose_name='Criado por'
    )
    recebido_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='ordens_recebidas',
        verbose_name='Recebido por'
    )
    data_envio = models.DateTimeField(auto_now_add=True, verbose_name='Data de Envio')
    data_recebimento = models.DateTimeField(null=True, blank=True, verbose_name='Data de Recebimento')

    class Meta:
        verbose_name = 'Ordem de Transferência'
        verbose_name_plural = 'Ordens de Transferência'
        ordering = ['-data_envio']

    def __str__(self):
        return f'OT-{self.numero} | {self.local_origem} → {self.local_destino} | {self.get_status_display()}'

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
    def confirmar_recebimento(self, usuario):
        from estoque.models import Estoque
        from django.utils import timezone

        if self.status != self.STATUS_TRANSITO:
            raise ValueError('Apenas ordens em trânsito podem ser confirmadas.')

        for item in self.itens.all():
            saldo_destino = Estoque.get_or_create_saldo(item.produto, self.local_destino)
            saldo_destino.adicionar(item.quantidade)

        self.status = self.STATUS_RECEBIDO
        self.recebido_por = usuario
        self.data_recebimento = timezone.now()
        self.save()

    @transaction.atomic
    def cancelar(self):
        from estoque.models import Estoque

        if self.status != self.STATUS_TRANSITO:
            raise ValueError('Apenas ordens em trânsito podem ser canceladas.')

        for item in self.itens.all():
            saldo_origem = Estoque.get_or_create_saldo(item.produto, self.local_origem)
            saldo_origem.adicionar(item.quantidade)

        self.status = self.STATUS_CANCELADO
        self.save()


class ItemOrdemTransferencia(models.Model):
    ordem = models.ForeignKey(
        OrdemTransferencia,
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
        verbose_name = 'Item da Ordem'
        verbose_name_plural = 'Itens da Ordem'

    def __str__(self):
        return f'{self.produto.nome} — {self.quantidade}'