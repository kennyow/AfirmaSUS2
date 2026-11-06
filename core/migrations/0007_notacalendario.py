from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0006_add_ata_reuniao')]
    operations = [
        migrations.CreateModel(
            name='NotaCalendario',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('dados', models.JSONField()),
            ],
        ),
    ]
