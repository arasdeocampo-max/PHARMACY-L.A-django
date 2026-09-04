from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacy", "0004_integrity_constraints_checkout_key")]

    operations = [
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.UniqueConstraint(
                condition=models.Q(method="gcash") & ~models.Q(payment_reference=""),
                fields=("method", "payment_reference"),
                name="unique_gcash_payment_reference",
            ),
        ),
        migrations.CreateModel(
            name="SaleAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("adjustment_type", models.CharField(choices=[("refund", "Refund"), ("void", "Void"), ("discount", "Discount")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))])),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="approved_sale_adjustments", to="auth.user")),
                ("requested_by", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="requested_sale_adjustments", to="auth.user")),
                ("sale", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="adjustments", to="pharmacy.salerecord")),
            ],
        ),
        migrations.AddConstraint(
            model_name="saleadjustment",
            constraint=models.CheckConstraint(check=models.Q(amount__gt=0), name="sale_adjustment_amount_positive"),
        ),
    ]