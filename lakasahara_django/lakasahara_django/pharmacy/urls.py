from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard_view, name="admin_dashboard"),
    path(
        "dashboard/pharmacist/",
        views.pharmacist_dashboard_view,
        name="pharmacist_dashboard",
    ),
    path("dashboard/staff/", views.staff_dashboard_view, name="staff_dashboard"),
    path("products/", views.products_view, name="products"),
    path("products/add/", views.product_add_view, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit_view, name="product_edit"),
    path(
        "products/<int:pk>/edit-form/",
        views.product_edit_view,
        name="product_edit_form",
    ),
    path("products/<int:pk>/delete/", views.product_delete_view, name="product_delete"),
    path("inventory/", views.inventory_view, name="inventory"),
    path("inventory/batch/add/", views.add_batch_view, name="add_batch"),
    path(
        "inventory/batch/add/<int:product_id>/",
        views.add_batch_view,
        name="add_batch_for",
    ),
    path(
        "inventory/batch/<int:batch_id>/dispose/",
        views.dispose_batch_view,
        name="dispose_batch",
    ),
    path(
        "inventory/batch/<int:batch_id>/return/",
        views.return_batch_view,
        name="return_batch",
    ),
    path("sales/", views.sales_view, name="sales"),
    path("sales/checkout/", views.checkout_view, name="checkout"),
    path("sales/adjustments/request/", views.request_sale_adjustment_view, name="request_sale_adjustment"),
    path("sales/adjustments/<int:adjustment_id>/approve/", views.approve_sale_adjustment_view, name="approve_sale_adjustment"),
    path("reports/", views.reports_view, name="reports"),
    path("expiry/", views.expiry_view, name="expiry"),
]
