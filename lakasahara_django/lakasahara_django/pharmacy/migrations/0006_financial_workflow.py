from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("pharmacy", "0005_sale_adjustment_and_gcash_constraint")]

    operations = [
        migrations.AddField(
            model_name="salerecord",
            name="state",
            field=models.CharField(
                choices=[
                    ("completed", "Completed"),
                    ("partially-refunded", "Partially Refunded"),
                    ("refunded", "Refunded"),
                    ("voided", "Voided"),
                ],
                default="completed",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="saleadjustment",
            name="rejected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="saleadjustment",
            name="rejected_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="rejected_sale_adjustments",
                to="auth.user",
            ),
        ),
        migrations.CreateModel(
            name="SaleItemAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.IntegerField(validators=[MinValueValidator(1)])),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sale_allocations", to="pharmacy.batch")),
                ("sale_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="allocations", to="pharmacy.saleitem")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(check=models.Q(quantity__gte=1), name="sale_allocation_quantity_positive"),
                ],
            },
        ),
        migrations.CreateModel(
            name="FinancialTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_id", models.CharField(max_length=30, unique=True)),
                ("transaction_type", models.CharField(choices=[("sale", "Sale"), ("refund", "Refund"), ("void", "Void")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))])),
                ("method", models.CharField(default="cash", max_length=20)),
                ("payment_reference", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("adjustment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="financial_transaction", to="pharmacy.saleadjustment")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="financial_transactions", to="pharmacy.salerecord")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(check=models.Q(amount__gt=0), name="financial_transaction_amount_positive"),
                ],
            },
        ),
    ]