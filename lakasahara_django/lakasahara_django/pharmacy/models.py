from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date
from decimal import Decimal


class UserProfile(models.Model):
    ROLES = [
        ("admin", "Administrator"),
        ("pharmacist", "Pharmacist"),
        ("staff", "Counter Staff"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLES, default="staff")

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=200, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.target}"


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    payment_terms = models.CharField(max_length=50, blank=True, default="Net 30")
    lead_days = models.IntegerField(default=3)

    def __str__(self):
        return self.name


class Product(models.Model):
    TYPE_CHOICES = [("OTC", "OTC"), ("RX", "Prescription")]
    CATEGORY_CHOICES = [("Medicine", "Medicine"), ("Medical Supply", "Medical Supply")]
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=100, choices=CATEGORY_CHOICES, default="Medicine"
    )
    kind = models.CharField(max_length=100, default="Tablet")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="OTC")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    reorder_level = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    shelf = models.CharField(max_length=50)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(price__gte=Decimal("0.01")), name="product_price_positive"),
            models.CheckConstraint(check=models.Q(reorder_level__gte=0), name="product_reorder_non_negative"),
        ]

    @property
    def stock(self):
        return sum(
            b.quantity
            for b in self.batches.filter(
                status__in=["good", "expiring-soon", "expiring-warning"]
            )
        )

    @property
    def stock_label(self):
        s = self.stock
        if s == 0:
            return ("Out of Stock", "badge-danger")
        if s <= self.reorder_level:
            return ("Low Stock", "badge-warning")
        return ("In Stock", "badge-success")

    def __str__(self):
        return self.name


def compute_batch_status(expiry_date):
    days = (expiry_date - date.today()).days
    if days < 0:
        return "expired"
    if days <= 30:
        return "expiring-soon"
    if days <= 60:
        return "expiring-warning"
    return "good"


class Batch(models.Model):
    STATUS_CHOICES = [
        ("good", "Good"),
        ("expiring-warning", "Expiring <60d"),
        ("expiring-soon", "Expiring <30d"),
        ("expired", "Expired"),
        ("disposed", "Disposed"),
    ]
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="batches"
    )
    batch_number = models.CharField(max_length=100)
    expiry = models.DateField()
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    supplier_name = models.CharField(max_length=200, blank=True)
    shelf = models.CharField(max_length=50, blank=True)
    received_date = models.DateField(default=date.today)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="good")
    disposed_qty = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    disposed_date = models.DateField(null=True, blank=True)
    disposed_by = models.CharField(max_length=200, blank=True)
    disposal_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=0), name="batch_quantity_non_negative"),
            models.CheckConstraint(check=models.Q(disposed_qty__isnull=True) | models.Q(disposed_qty__gte=0), name="batch_disposed_qty_non_negative"),
        ]

    def days_until_expiry(self):
        return (self.expiry - date.today()).days

    def save(self, *args, **kwargs):
        if self.status != "disposed":
            self.status = compute_batch_status(self.expiry)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} — {self.batch_number}"


class SaleRecord(models.Model):
    transaction_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    cash_given = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])
    method = models.CharField(max_length=20, default="cash")
    payment_reference = models.CharField(max_length=100, blank=True)
    checkout_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(discount__gte=0), name="sale_discount_non_negative"),
            models.CheckConstraint(check=models.Q(total__gte=0), name="sale_total_non_negative"),
            models.CheckConstraint(check=models.Q(cash_given__gte=0), name="sale_cash_non_negative"),
            models.UniqueConstraint(
                condition=models.Q(method="gcash") & ~models.Q(payment_reference=""),
                fields=("method", "payment_reference"),
                name="unique_gcash_payment_reference",
            ),
        ]

    @property
    def change(self):
        return max(0, float(self.cash_given) - float(self.total))

    def __str__(self):
        return self.transaction_id


class SaleItem(models.Model):
    sale = models.ForeignKey(SaleRecord, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    qty = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(qty__gte=1), name="sale_item_qty_positive"),
            models.CheckConstraint(check=models.Q(price__gte=Decimal("0.01")), name="sale_item_price_positive"),
        ]

    @property
    def line_total(self):
        return float(self.qty) * float(self.price)

    def __str__(self):
        return f"{self.product_name} x{self.qty}"


class SaleAdjustment(models.Model):
    TYPE_CHOICES = [("refund", "Refund"), ("void", "Void"), ("discount", "Discount")]
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]

    sale = models.ForeignKey(SaleRecord, on_delete=models.PROTECT, related_name="adjustments")
    adjustment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    reason = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="requested_sale_adjustments")
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_sale_adjustments")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="sale_adjustment_amount_positive"),
        ]
