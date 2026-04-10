from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0004_alter_partido_canales_bolaloca'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='minuto',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Minuto actual del partido (solo durante partidos en vivo)',
            ),
        ),
    ]
