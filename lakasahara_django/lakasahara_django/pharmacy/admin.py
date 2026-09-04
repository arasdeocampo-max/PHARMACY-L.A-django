from django.contrib import admin
from .models import UserProfile, Supplier, Product, Batch, SaleAdjustment, SaleRecord, SaleItem


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    list_filter = ["role"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "payment_terms", "lead_days"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "barcode",
        "category",
        "type",
        "price",
        "reorder_level",
        "shelf",
    ]
    list_filter = ["category", "type"]
    search_fields = ["name", "barcode"]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["product", "batch_number", "expiry", "quantity", "status"]
    list_filter = ["status"]
    search_fields = ["batch_number", "product__name"]


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ["product", "product_name", "qty", "price"]


@admin.register(SaleRecord)
class SaleRecordAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ["transaction_id", "total", "cashier", "method", "created_at"]
    search_fields = ["transaction_id"]
    readonly_fields = [
        "transaction_id",
        "created_at",
        "subtotal",
        "discount",
        "total",
        "cash_given",
        "method",
        "payment_reference",
        "checkout_key",
        "cashier",
    ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleAdjustment)
class SaleAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["sale", "adjustment_type", "amount", "status", "requested_by", "approved_by", "created_at"]
    list_filter = ["adjustment_type", "status"]
    readonly_fields = ["sale", "adjustment_type", "amount", "reason", "requested_by", "approved_by", "status", "created_at", "approved_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
