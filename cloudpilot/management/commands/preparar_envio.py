from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Cria o grupo de envio e inclui apenas contas existentes explicitamente indicadas.'

    def add_arguments(self, parser):
        parser.add_argument('usuarios', nargs='*')

    def handle(self, *args, **options):
        users = list(User.objects.filter(username__in=options['usuarios'], is_active=True))
        if len(users) != len(set(options['usuarios'])):
            raise CommandError('Uma das contas indicadas não existe ou está inativa. Nenhuma permissão foi alterada.')
        permission = Permission.objects.get(content_type__app_label='cloudpilot', codename='add_arquivopublico')
        group, _ = Group.objects.get_or_create(name='Envio de arquivos')
        group.permissions.add(permission)
        for user in users:
            user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(f'Grupo preparado; {len(users)} conta(s) autorizada(s).'))
