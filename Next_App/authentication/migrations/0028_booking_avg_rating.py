# Generated by Django 5.1.7 on 2025-06-04 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0027_alter_partner_experience_alter_partner_is_verified_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='avg_rating',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=3, null=True),
        ),
    ]
