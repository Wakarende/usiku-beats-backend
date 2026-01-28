from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0022_artist_name_alter_artist_profile'),  # Replace with actual previous migration
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='difficulty',
            field=models.CharField(max_length=50, null=True),  # Adjust field type and options as needed
        ),
    ]