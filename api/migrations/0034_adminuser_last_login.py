"""Add last_login timestamp to AdminUser, updated on every /auth/me/ call."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0033_song_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminuser',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
