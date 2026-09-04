from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0003_salerecord_payment_reference"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))]),
        ),
        migrations.AlterField(
            model_name="product",
            name="reorder_level",
            field=models.IntegerField(default=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="batch",
            name="quantity",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="batch",
            name="disposed_qty",
            field=models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="salerecord",
            name="discount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(Decimal("0"))]),
        ),
        migrations.AlterField(
            model_name="salerecord",
            name="total",
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0"))]),
        ),
        migrations.AlterField(
            model_name="salerecord",
            name="cash_given",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(Decimal("0"))]),
        ),
        migrations.AlterField(
            model_name="saleitem",
            name="qty",
            field=models.IntegerField(validators=[MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name="saleitem",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))]),
        ),
        migrations.AddField(
            model_name="salerecord",
            name="checkout_key",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(check=models.Q(price__gte=Decimal("0.01")), name="product_price_positive"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(check=models.Q(reorder_level__gte=0), name="product_reorder_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="batch",
            constraint=models.CheckConstraint(check=models.Q(quantity__gte=0), name="batch_quantity_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="batch",
            constraint=models.CheckConstraint(check=models.Q(disposed_qty__isnull=True) | models.Q(disposed_qty__gte=0), name="batch_disposed_qty_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.CheckConstraint(check=models.Q(discount__gte=0), name="sale_discount_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.CheckConstraint(check=models.Q(total__gte=0), name="sale_total_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.CheckConstraint(check=models.Q(cash_given__gte=0), name="sale_cash_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="saleitem",
            constraint=models.CheckConstraint(check=models.Q(qty__gte=1), name="sale_item_qty_positive"),
        ),
        migrations.AddConstraint(
            model_name="saleitem",
            constraint=models.CheckConstraint(check=models.Q(price__gte=Decimal("0.01")), name="sale_item_price_positive"),
        ),
    ]