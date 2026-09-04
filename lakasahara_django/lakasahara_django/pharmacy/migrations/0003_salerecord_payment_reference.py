from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0002_auditevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="salerecord",
            name="payment_reference",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]