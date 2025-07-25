# Generated by Django 5.1.7 on 2025-05-09 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0017_booking_partner_accepted_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fcmtoken",
            name="token",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterUniqueTogether(
            name="fcmtoken",
            unique_together={("user", "token")},
        ),
    ]
