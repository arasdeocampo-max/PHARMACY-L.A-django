from datetime import date

from .models import Product


def notifications(request):
    if not request.user.is_authenticated:
        return {}

    products = Product.objects.prefetch_related("batches").all()
    alerts = []
    for product in products:
        if product.stock == 0:
            alerts.append({
                "kind": "critical",
                "title": "Critical: Out of Stock",
                "message": f"{product.name} has 0 units remaining.",
            })
        elif product.stock <= product.reorder_level:
            alerts.append({
                "kind": "warning",
                "title": "Low Stock Warning",
                "message": f"{product.name} has only {product.stock} units left.",
            })

        for batch in product.batches.exclude(status="disposed"):
            days = (batch.expiry - date.today()).days
            if days < 0:
                alerts.append({
                    "kind": "critical",
                    "title": "Expiry Alert",
                    "message": f"{product.name} expired on {batch.expiry}.",
                })
            elif days <= 30:
                alerts.append({
                    "kind": "warning",
                    "title": "Expiry Alert",
                    "message": f"{product.name} expires in {days} days.",
                })

    critical_count = sum(1 for alert in alerts if alert["kind"] == "critical")
    warning_count = sum(1 for alert in alerts if alert["kind"] == "warning")
    return {
        "notification_alerts": alerts[:12],
        "notification_total": len(alerts),
        "notification_critical_count": critical_count,
        "notification_warning_count": warning_count,
        "notification_info_count": 0,
    }
