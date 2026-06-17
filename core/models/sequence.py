from django.db import models, transaction


class Sequence(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nome')
    last = models.PositiveIntegerField(default=0, verbose_name='Último valor')

    class Meta:
        verbose_name = 'Sequência'
        verbose_name_plural = 'Sequências'

    def __str__(self):
        return f'{self.name}: {self.last}'

    @classmethod
    def next(cls, name: str, start: int = 3000) -> int:
        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(
                name=name,
                defaults={'last': start - 1}
            )
            seq.last += 1
            seq.save(update_fields=['last'])
            return seq.last

    @classmethod
    def next_formatted(cls, name: str, start: int = 3000) -> str:
        n = cls.next(name, start)
        return str(n).zfill(6)