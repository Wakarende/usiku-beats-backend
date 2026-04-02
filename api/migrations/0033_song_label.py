"""Add label FK to Song model so individual songs can override the artist's default label."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0032_song_is_library'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='label',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='songs',
                to='api.label',
            ),
        ),
    ]
