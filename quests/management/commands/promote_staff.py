from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = 'Ставит пользователю is_staff (и по желанию superuser)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='логин')
        parser.add_argument(
            '--superuser',
            action='store_true',
            help='ещё и is_superuser',
        )

    def handle(self, *args, **options):
        username = options['username'].strip()
        if not username:
            raise CommandError('нужен username')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(
                f'нет такого: {username} (сначала register в API)'
            ) from exc

        user.is_staff = True
        if options['superuser']:
            user.is_superuser = True
        user.save(update_fields=['is_staff', 'is_superuser'] if options['superuser'] else ['is_staff'])

        self.stdout.write(
            self.style.SUCCESS(
                f'готово: {username}, staff=1'
                + (' super=1' if options['superuser'] else '')
            )
        )
        self.stdout.write('токен можно заново взять через POST /api/auth/token/')
