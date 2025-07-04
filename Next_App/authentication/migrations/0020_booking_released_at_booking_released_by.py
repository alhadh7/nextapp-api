# Generated by Django 5.1.7 on 2025-05-10 12:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0019_bookingextension_partner_accepted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="released_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="released_bookings",
                to="authentication.partner",
            ),
        ),
    ]
