# Generated by Django 5.1.7 on 2025-05-03 06:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "authentication",
            "0012_partner_bank_account_number_partner_bank_username_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="partner",
            name="last_payment_date",
        ),
    ]
