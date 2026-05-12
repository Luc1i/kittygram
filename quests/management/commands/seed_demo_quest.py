from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cats.models import Cat
from quests.models import QuestStep, QuestWeek


class Command(BaseCommand):
    help = 'Добавляет тестовую неделю demo-week на текущую неделю и пару шагов'

    def handle(self, *args, **options):
        today = timezone.now().date()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)

        week, created = QuestWeek.objects.get_or_create(
            slug='demo-week',
            defaults={
                'title': 'Демо-неделя',
                'description': 'для проверки',
                'week_start': start,
                'week_end': end,
                'is_published': True,
                'max_participants': 100,
            },
        )
        if not created:
            week.week_start = start
            week.week_end = end
            week.is_published = True
            week.save(update_fields=['week_start', 'week_end', 'is_published'])

        cat, _ = Cat.objects.get_or_create(
            name='Мурзик',
            defaults={'color': 'рыжий', 'birth_year': 2020},
        )

        if not week.steps.exists():
            QuestStep.objects.create(
                quest_week=week,
                order=1,
                title='Найди кота в каталоге',
                description='кот из каталога, id посмотри в /cats/',
                points=5,
                related_cat=cat,
            )
            QuestStep.objects.create(
                quest_week=week,
                order=2,
                title='Второй шаг',
                description='после первого',
                points=10,
                related_cat=None,
            )
            self.stdout.write(self.style.SUCCESS('шаги добавлены'))
        else:
            self.stdout.write('шаги уже есть')

        self.stdout.write(self.style.SUCCESS(f'Неделя id={week.pk} slug={week.slug} {start}…{end}'))
