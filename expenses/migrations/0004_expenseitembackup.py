# Generated for SMS item cleanup — backup table for reversible data migration.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0003_budget"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseItemBackup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "original_item",
                    models.CharField(max_length=100, verbose_name="원본 항목"),
                ),
                (
                    "normalized_item",
                    models.CharField(max_length=100, verbose_name="정규화 항목"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "expense",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="item_backups",
                        to="expenses.expense",
                        verbose_name="지출",
                    ),
                ),
            ],
            options={
                "db_table": "expense_item_backup",
                "ordering": ["-created_at"],
            },
        ),
    ]
