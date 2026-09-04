import csv
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .forms import AddUserForm, BatchForm, DisposeForm, ProductForm, is_valid_username
from .audit import record_audit
from .models import (
    AuditEvent,
    Batch,
    FinancialTransaction,
    Product,
    SaleAdjustment,
    SaleItem,
    SaleItemAllocation,
    SaleRecord,
    Supplier,
    compute_batch_status,
)
from lakasahara.settings import DEMO_LOGIN_ENABLED


def get_role(request):
    try:
        return request.user.profile.role
    except Exception:
        return None


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if get_role(request) not in roles:
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


DEMO_CREDS = []


def get_demo_creds():
    if not DEMO_LOGIN_ENABLED:
        return []
    return [
        {
            "username": "admin",
            "password": "admin123",
            "label": "Administrator",
            "desc": "Full system access",
        },
        {
            "username": "pharmacist",
            "password": "pharma123",
            "label": "Pharmacist",
            "desc": "Inventory & dispensing",
        },
        {
            "username": "staff",
            "password": "staff123",
            "label": "Counter Staff",
            "desc": "Sales POS access",
        },
    ]


def _login_fail_key(username):
    return f"login_failures:{(username or '').strip().lower()}"


def _login_attempts_exceeded(username):
    key = _login_fail_key(username)
    attempts = cache.get(key, 0)
    return attempts >= 5


def _record_failed_login(username):
    key = _login_fail_key(username)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, 900)
    return attempts


def _clear_failed_login(username):
    cache.delete(_login_fail_key(username))


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = ""
    demo_creds = get_demo_creds()
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if not is_valid_username(username):
            return render(
                request,
                "login.html",
                {
                    "error": "Enter a valid username, not an email address or emoji.",
                    "demo_creds": demo_creds,
                },
            )
        user = authenticate(
            request,
            username=username,
            password=request.POST.get("password"),
        )
        if user:
            _clear_failed_login(username)
            login(request, user)
            record_audit(user, "Login", user.username, "Successful login")
            return redirect("dashboard")

        attempts = _record_failed_login(username)
        if attempts >= 5:
            error = "Too many failed login attempts. Please wait 15 minutes before trying again."
        else:
            error = "Incorrect username or password."
        record_audit(None, "Failed Login", request.POST.get("username", ""), "Invalid credentials")
    return render(request, "login.html", {"error": error, "demo_creds": demo_creds})


def logout_view(request):
    record_audit(request.user, "Logout", request.user.username, "User logged out")
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard_view(request):
    role = get_role(request)
    if role == "admin":
        return redirect("admin_dashboard")
    if role == "pharmacist":
        return redirect("pharmacist_dashboard")
    if role == "staff":
        return redirect("staff_dashboard")
    logout(request)
    return redirect("login")


@login_required(login_url="login")
@role_required("admin")
def admin_dashboard_view(request):
    products = list(
        Product.objects.select_related("supplier").prefetch_related("batches").all()
    )
    users = User.objects.select_related("profile").all()
    sales = SaleRecord.objects.prefetch_related("items").order_by("-created_at")
    today = date.today()
    total_revenue = sum(float(s.total) for s in sales)
    low_stock = [p for p in products if 0 < p.stock <= p.reorder_level]
    out_of_stock = [p for p in products if p.stock == 0]
    expiring_soon = [
        p
        for p in products
        if any(
            (b.expiry - today).days <= 90 for b in p.batches.exclude(status="disposed")
        )
    ]
    add_form = AddUserForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_user":
            add_form = AddUserForm(request.POST)
            if add_form.is_valid():
                created_user = add_form.save()
                record_audit(request.user, "Create User", created_user.username, f"Role: {created_user.profile.role}")
                messages.success(request, "User created.")
                return redirect("admin_dashboard")
        elif action == "delete_user":
            target = get_object_or_404(User, pk=request.POST.get("user_id"))
            if target != request.user:
                target_name = target.username
                target.delete()
                record_audit(request.user, "Delete User", target_name, "User account deleted")
                messages.success(request, "User deleted.")
            return redirect("admin_dashboard")
    context = {
        "role": "admin",
        "products": products,
        "users": users,
        "sales": sales[:6],
        "audit_events": AuditEvent.objects.select_related("actor").all()[:8],
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "expiring_soon": expiring_soon,
        "total_revenue": total_revenue,
        "add_form": add_form,
        "kpis": [
            {
                "label": "Revenue To Date",
                "value": f"PHP {total_revenue:.2f}",
                "note": f"{sales.count()} transactions",
                "color": "#1c6e6e",
            },
            {
                "label": "Total Products",
                "value": len(products),
                "note": "in catalog",
                "color": "#2563eb",
            },
            {
                "label": "Low Stock Items",
                "value": len(low_stock),
                "note": f"{len(out_of_stock)} out of stock",
                "color": "#d97706",
            },
            {
                "label": "Expiring Soon",
                "value": len(expiring_soon),
                "note": "within 90 days",
                "color": "#dc2626",
            },
        ],
    }
    return render(request, "dashboard_admin.html", context)


@login_required(login_url="login")
@role_required("pharmacist")
def pharmacist_dashboard_view(request):
    products = list(Product.objects.prefetch_related("batches").all())
    today = date.today()
    expiring = []
    for p in products:
        active = list(p.batches.exclude(status="disposed"))
        if active:
            min_days = min((b.expiry - today).days for b in active)
            if min_days <= 180:
                expiring.append(
                    {
                        "product": p,
                        "days": min_days,
                        "expiry": min(active, key=lambda b: b.expiry).expiry,
                    }
                )
    expiring.sort(key=lambda x: x["days"])
    kpis = [
        {
            "label": "RX Products",
            "value": sum(1 for p in products if p.type == "RX"),
            "sub": "prescription items",
            "color": "#c23b56",
            "bg": "rgba(194,59,86,0.1)",
        },
        {
            "label": "Expiring ≤90d",
            "value": sum(1 for e in expiring if e["days"] <= 90),
            "sub": "need urgent review",
            "color": "#dc2626",
            "bg": "rgba(220,38,38,0.1)",
        },
        {
            "label": "Low Stock",
            "value": sum(1 for p in products if p.stock <= p.reorder_level),
            "sub": "below reorder level",
            "color": "#d97706",
            "bg": "rgba(245,158,11,0.12)",
        },
        {
            "label": "Healthy Stock",
            "value": sum(1 for p in products if p.stock > p.reorder_level),
            "sub": "above threshold",
            "color": "#15803d",
            "bg": "rgba(22,163,74,0.12)",
        },
    ]
    return render(
        request,
        "dashboard_pharmacist.html",
        {
            "role": "pharmacist",
            "products": products,
            "expiring": expiring,
            "kpis": kpis,
            "out_of_stock_count": sum(1 for p in products if p.stock == 0),
            "low_stock_count": sum(
                1 for p in products if 0 < p.stock <= p.reorder_level
            ),
        },
    )


@login_required(login_url="login")
@role_required("staff")
def staff_dashboard_view(request):
    products = Product.objects.filter(type="OTC").prefetch_related("batches")[:8]
    sales = SaleRecord.objects.filter(created_at__date=date.today()).order_by(
        "-created_at"
    )
    return render(
        request,
        "dashboard_staff.html",
        {
            "role": "staff",
            "products": products,
            "sales": sales,
            "today_revenue": sum(float(s.total) for s in sales),
            "transaction_count": sales.count(),
        },
    )


@login_required(login_url="login")
@role_required("admin")
def products_view(request):
    qs = Product.objects.select_related("supplier").prefetch_related("batches").all()
    search = request.GET.get("search", "")
    cat = request.GET.get("cat", "")
    ptype = request.GET.get("type", "")
    if search:
        qs = qs.filter(name__icontains=search) | Product.objects.filter(
            barcode__icontains=search
        )
    if cat:
        qs = qs.filter(category=cat)
    if ptype:
        qs = qs.filter(type=ptype)
    return render(
        request,
        "products.html",
        {
            "role": "admin",
            "products": qs,
            "suppliers": Supplier.objects.all(),
            "search": search,
            "cat": cat,
            "ptype": ptype,
        },
    )


@login_required(login_url="login")
@role_required("admin")
def product_add_view(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        product = form.save()
        record_audit(request.user, "Create Product", product.name, f"Barcode: {product.barcode}")
        messages.success(request, "Product added.")
        return redirect("products")
    return render(
        request,
        "product_form.html",
        {"form": form, "title": "Add Product", "role": "admin"},
    )


@login_required(login_url="login")
@role_required("admin")
def product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # For AJAX form request, return structured field data for safe client rendering.
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "GET"
    ):
        form = ProductForm(instance=product)
        fields = []
        for field in form:
            field_value = field.value()
            fields.append(
                {
                    "name": field.name,
                    "id": field.id_for_label,
                    "label": field.label,
                    "input_type": field.field.widget.input_type,
                    "value": "" if field_value is None else str(field_value),
                    "choices": (
                        [(str(value), str(label)) for value, label in field.field.choices]
                        if field.field.widget.input_type == "select"
                        else []
                    ),
                    "errors": [str(error) for error in field.errors],
                }
            )
        return JsonResponse({"fields": fields})

    # For regular GET requests
    if request.method == "GET":
        form = ProductForm(instance=product)
        return render(
            request,
            "product_form.html",
            {
                "form": form,
                "title": "Edit Product",
                "product": product,
                "role": "admin",
            },
        )

    # For POST requests (form submission)
    form = ProductForm(request.POST, instance=product)
    if form.is_valid():
        form.save()
        record_audit(request.user, "Update Product", product.name, f"Barcode: {product.barcode}")

        # If it's an AJAX request, return JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "message": "Product updated successfully"}
            )

        # Otherwise redirect
        messages.success(request, "Product updated.")
        return redirect("products")

    # If form is not valid and it's AJAX, return error JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        errors = {
            field: [str(e) for e in field_errors]
            for field, field_errors in form.errors.items()
        }
        return JsonResponse(
            {"success": False, "error": "Invalid form data", "errors": errors}
        )

    # Otherwise return the form template
    return render(
        request,
        "product_form.html",
        {"form": form, "title": "Edit Product", "product": product, "role": "admin"},
    )


@login_required(login_url="login")
@role_required("admin")
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()
        record_audit(request.user, "Delete Product", name, "Product and related batches deleted")
        messages.success(request, f"{name} deleted.")
        return redirect("products")
    return redirect("products")


@login_required(login_url="login")
@role_required("admin", "pharmacist")
def inventory_view(request):
    search = request.GET.get("search", "").strip()
    category = request.GET.get("cat", "")
    status = request.GET.get("status", "")
    products = (
        Product.objects.select_related("supplier").prefetch_related("batches").all()
    )

    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(barcode__icontains=search)
        )
    if category:
        products = products.filter(category=category)

    all_products = list(products)
    for product in all_products:
        product.receive_form = BatchForm(
            initial={
                "product": product,
                "supplier_name": product.supplier.name if product.supplier else "",
                "shelf": product.shelf,
            }
        )
        batches = list(product.batches.all())
        product.total_qty = sum(batch.quantity for batch in batches)
        product.expired_qty = sum(
            batch.quantity for batch in batches if batch.status == "expired"
        )

    if status == "in_stock":
        all_products = [p for p in all_products if p.stock > p.reorder_level]
    elif status == "low_stock":
        all_products = [p for p in all_products if 0 < p.stock <= p.reorder_level]
    elif status == "out_of_stock":
        all_products = [p for p in all_products if p.stock == 0]

    all_inventory_products = list(
        Product.objects.prefetch_related("batches").all()
    )
    low_stock = sum(
        1 for p in all_inventory_products if 0 < p.stock <= p.reorder_level
    )
    out_of_stock = sum(1 for p in all_inventory_products if p.stock == 0)
    return render(
        request,
        "inventory.html",
        {
            "role": get_role(request),
            "products": all_products,
            "search": search,
            "cat": category,
            "status_filter": status,
            "today": date.today(),
            "total_products": len(all_products),
            "low_stock_count": low_stock,
            "out_of_stock_count": out_of_stock,
            "expired_batches": Batch.objects.filter(status="expired").count(),
            "expiring_soon": Batch.objects.filter(status="expiring-soon").count(),
        },
    )


@login_required(login_url="login")
@role_required("admin", "pharmacist")
def add_batch_view(request, product_id=None):
    product = get_object_or_404(Product, pk=product_id) if product_id else None
    initial = (
        {
            "product": product,
            "supplier_name": (
                product.supplier.name if product and product.supplier else ""
            ),
            "shelf": product.shelf if product else "",
        }
        if product
        else {}
    )
    form = BatchForm(request.POST or None, initial=initial)
    if form.is_valid():
        b = form.save(commit=False)
        b.status = compute_batch_status(b.expiry)
        b.save()
        record_audit(request.user, "Receive Batch", b.batch_number, f"Product: {b.product.name}; Quantity: {b.quantity}")
        messages.success(request, "Stock batch received.")
        return redirect(f"{reverse('inventory')}?open_batch={b.product_id}")
    return render(
        request,
        "add_batch.html",
        {
            "form": form,
            "product": product,
            "products": Product.objects.all(),
            "role": get_role(request),
        },
    )


@login_required(login_url="login")
@role_required("admin", "pharmacist")
@require_POST
def dispose_batch_view(request, batch_id):
    batch = get_object_or_404(Batch, pk=batch_id)
    form = DisposeForm(request.POST, initial={"qty": batch.quantity})
    if form.is_valid():
        with transaction.atomic():
            batch = Batch.objects.select_for_update().select_related("product").get(pk=batch_id)
            quantity = form.cleaned_data["qty"]
            if batch.status == "disposed" or batch.quantity <= 0:
                form.add_error(None, "This batch is no longer available for disposal.")
            elif quantity > batch.quantity:
                form.add_error("qty", "Quantity cannot exceed available stock.")
            else:
                batch.disposed_qty = quantity
                batch.disposed_date = date.today()
                batch.disposed_by = form.cleaned_data["authorized_by"]
                batch.disposal_reason = form.cleaned_data["reason"]
                batch.quantity -= quantity
                batch.status = "disposed"
                batch.save(update_fields=["disposed_qty", "disposed_date", "disposed_by", "disposal_reason", "quantity", "status"])
                record_audit(request.user, "Dispose Batch", batch.batch_number, f"Product: {batch.product.name}; Quantity: {quantity}; Reason: {form.cleaned_data['reason']}")
                messages.success(request, f"Batch {batch.batch_number} disposed.")
                return redirect("inventory")
    return render(
        request,
        "dispose_batch.html",
        {"form": form, "batch": batch, "role": get_role(request)},
    )


@require_POST
@login_required(login_url="login")
@role_required("admin", "pharmacist")
def return_batch_view(request, batch_id):
    reason = request.POST.get("reason", "").strip()
    if reason not in {"Damaged Product/Medicine", "Near Expiry", "Expired"}:
        messages.error(request, "Please select a valid supplier return reason.")
        return redirect("expiry")
    with transaction.atomic():
        batch = get_object_or_404(Batch.objects.select_for_update().select_related("product"), pk=batch_id)
        if batch.status == "disposed" or batch.quantity <= 0:
            messages.error(request, "This batch is no longer available for return.")
            return redirect("expiry")
        quantity = batch.quantity
        batch.disposed_qty = quantity
        batch.disposed_date = date.today()
        batch.disposed_by = request.user.get_full_name() or request.user.username
        batch.disposal_reason = f"Returned to supplier: {reason}"
        batch.quantity = 0
        batch.status = "disposed"
        batch.save(update_fields=["disposed_qty", "disposed_date", "disposed_by", "disposal_reason", "quantity", "status"])
        record_audit(request.user, "Return Batch", batch.batch_number, f"Product: {batch.product.name}; Quantity: {quantity}; Reason: {reason}")
    messages.success(request, f"Confirmed: batch {batch.batch_number} returned to supplier.")
    return redirect("expiry")


@login_required(login_url="login")
@role_required("staff")
def sales_view(request):
    products_data = [
        {
            "id": p.id,
            "name": p.name,
            "barcode": p.barcode,
            "category": p.category,
            "kind": p.kind,
            "type": p.type,
            "price": float(p.price),
            "stock": p.stock,
            "image_url": p.image_url,
        }
        for p in Product.objects.prefetch_related("batches").all()
        if p.stock > 0
    ]
    return render(
        request,
        "sales.html",
        {
            "role": get_role(request),
            "products_json": json.dumps(products_data),
            "recent_sales": SaleRecord.objects.prefetch_related("items").order_by(
                "-created_at"
            )[:5],
        },
    )


@login_required(login_url="login")
@role_required("staff")
@require_POST
def checkout_view(request):
    idempotency_key = ""
    try:
        data = json.loads(request.body)
        idempotency_key = str(data.get("idempotency_key", "")).strip()
        if not idempotency_key or len(idempotency_key) > 64:
            return JsonResponse({"error": "A valid checkout idempotency key is required"}, status=400)
        existing_sale = SaleRecord.objects.filter(checkout_key=idempotency_key).first()
        if existing_sale:
            return JsonResponse(_sale_payload(existing_sale, duplicate=True))
        cart = data.get("cart", [])
        if not cart:
            return JsonResponse({"error": "Cart is empty"}, status=400)
        try:
            discount = Decimal(str(data.get("discount", "0")))
            cash_given = Decimal(str(data.get("cash_given", "0")))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({"error": "Invalid payment values"}, status=400)
        if discount < 0 or cash_given < 0:
            return JsonResponse({"error": "Payment values cannot be negative"}, status=400)
        method = str(data.get("method", "cash")).lower()
        payment_reference = str(data.get("payment_reference", "")).strip()
        if method not in {"cash", "gcash"}:
            return JsonResponse({"error": "Invalid payment method"}, status=400)
        if method == "gcash" and not payment_reference:
            return JsonResponse({"error": "GCash reference number is required"}, status=400)
        if method == "gcash" and not (payment_reference.isascii() and payment_reference.isdigit()):
            return JsonResponse({"error": "GCash reference number must contain digits only"}, status=400)
        if method == "gcash" and SaleRecord.objects.filter(method="gcash", payment_reference=payment_reference).exists():
            return JsonResponse({"error": "GCash reference number has already been used"}, status=400)
        if discount > 0 and get_role(request) != "admin":
            return JsonResponse({"error": "Discount requires admin approval"}, status=403)
        requested = []
        seen_product_ids = set()
        for item in cart:
            try:
                product_id = int(item["id"])
                quantity = int(item["qty"])
            except (KeyError, TypeError, ValueError):
                return JsonResponse({"error": "Invalid cart item"}, status=400)
            if product_id in seen_product_ids:
                return JsonResponse({"error": "Duplicate cart item"}, status=400)
            if quantity < 1 or quantity > 10000:
                return JsonResponse({"error": "Invalid quantity"}, status=400)
            seen_product_ids.add(product_id)
            requested.append((product_id, quantity))

        with transaction.atomic():
            authoritative_items = []
            for product_id, quantity in requested:
                product = Product.objects.get(pk=product_id)
                batches = list(
                    product.batches.select_for_update()
                    .filter(
                        status__in=["good", "expiring-soon", "expiring-warning"],
                    )
                    .order_by("expiry")
                )
                authoritative_items.append({
                    "product": product,
                    "quantity": quantity,
                    "price": product.price,
                    "batches": batches,
                })

            existing_sale = SaleRecord.objects.filter(checkout_key=idempotency_key).first()
            if existing_sale:
                return JsonResponse(_sale_payload(existing_sale, duplicate=True))

            for item in authoritative_items:
                available = sum(batch.quantity for batch in item["batches"])
                if available < item["quantity"]:
                    return JsonResponse({"error": f"Insufficient stock for {item['product'].name}"}, status=400)

            subtotal = sum(
                item["price"] * item["quantity"]
                for item in authoritative_items
            )
            if discount > subtotal:
                return JsonResponse({"error": "Discount exceeds subtotal"}, status=400)
            total = subtotal - discount
            if method == "cash" and cash_given < total:
                return JsonResponse({"error": "Cash tendered is less than total"}, status=400)
            if method == "gcash":
                cash_given = Decimal("0")

            txn_id = f"TXN-{uuid.uuid4().hex[:16].upper()}"
            sale = SaleRecord.objects.create(
                transaction_id=txn_id,
                subtotal=subtotal,
                discount=discount,
                total=total,
                cash_given=cash_given,
                method=method,
                payment_reference=payment_reference,
                checkout_key=idempotency_key,
                cashier=request.user,
            )
            FinancialTransaction.objects.create(
                transaction_id=txn_id,
                sale=sale,
                transaction_type="sale",
                amount=total,
                method=method,
                payment_reference=payment_reference,
            )
            for item in authoritative_items:
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    product=item["product"],
                    product_name=item["product"].name,
                    qty=item["quantity"],
                    price=item["price"],
                )
                remaining = item["quantity"]
                for batch in item["batches"]:
                    take = min(batch.quantity, remaining)
                    batch.quantity -= take
                    batch.save(update_fields=["quantity", "status"])
                    SaleItemAllocation.objects.create(
                        sale_item=sale_item,
                        batch=batch,
                        quantity=take,
                    )
                    remaining -= take
                    if remaining == 0:
                        break
                if remaining:
                    raise ValueError("Inventory deduction incomplete")
            record_audit(request.user, "Complete Sale", txn_id, f"Total: PHP {total:.2f}; Items: {len(authoritative_items)}")
        return JsonResponse(_sale_payload(sale))
    except IntegrityError:
        existing_sale = SaleRecord.objects.filter(checkout_key=idempotency_key).first()
        if existing_sale:
            return JsonResponse(_sale_payload(existing_sale, duplicate=True))
        return JsonResponse({"error": "Checkout could not be completed"}, status=409)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


def _sale_payload(sale, duplicate=False):
    return {
        "success": True,
        "duplicate": duplicate,
        "transaction_id": sale.transaction_id,
        "total": float(sale.total),
        "change": sale.change,
        "subtotal": float(sale.subtotal),
        "discount": float(sale.discount),
        "cash_given": float(sale.cash_given),
        "method": sale.method,
        "payment_reference": sale.payment_reference,
        "date": sale.created_at.strftime("%B %d, %Y"),
        "time": sale.created_at.strftime("%I:%M:%S %p"),
        "items": [
            {"name": item.product_name, "qty": item.qty, "price": float(item.price)}
            for item in sale.items.all()
        ],
    }


@require_POST
@login_required(login_url="login")
@role_required("admin", "staff")
def request_sale_adjustment_view(request):
    try:
        data = json.loads(request.body)
        sale = get_object_or_404(SaleRecord, pk=data.get("sale_id"))
        adjustment_type = str(data.get("adjustment_type", "")).lower()
        reason = str(data.get("reason", "")).strip()
        amount = Decimal(str(data.get("amount", "0")))
    except (json.JSONDecodeError, InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Invalid adjustment request"}, status=400)
    if adjustment_type not in {"refund", "void", "discount"} or not reason or amount <= 0:
        return JsonResponse({"error": "Invalid adjustment details"}, status=400)
    if amount > sale.total:
        return JsonResponse({"error": "Adjustment exceeds sale total"}, status=400)
    adjustment = SaleAdjustment.objects.create(
        sale=sale,
        adjustment_type=adjustment_type,
        amount=amount,
        reason=reason,
        requested_by=request.user,
    )
    record_audit(request.user, "Request Sale Adjustment", sale.transaction_id, f"Type: {adjustment_type}; Amount: PHP {amount:.2f}")
    return JsonResponse({"success": True, "adjustment_id": adjustment.pk, "status": adjustment.status}, status=201)


@require_POST
@login_required(login_url="login")
@role_required("admin")
def approve_sale_adjustment_view(request, adjustment_id):
    with transaction.atomic():
        adjustment = get_object_or_404(SaleAdjustment.objects.select_for_update(), pk=adjustment_id)
        if adjustment.status != "pending":
            return JsonResponse({"error": "Adjustment is no longer pending"}, status=409)
        sale = SaleRecord.objects.select_for_update().get(pk=adjustment.sale_id)
        if adjustment.adjustment_type in {"refund", "void"}:
            if sale.state == "voided" or (adjustment.adjustment_type == "void" and sale.state != "completed"):
                return JsonResponse({"error": "Sale is no longer eligible for this adjustment"}, status=409)
            if adjustment.adjustment_type == "void" and adjustment.amount != sale.total:
                return JsonResponse({"error": "A void must reverse the full sale total"}, status=400)
            refunded = sum(
                transaction.amount
                for transaction in sale.financial_transactions.filter(transaction_type="refund")
            )
            if adjustment.amount + refunded > sale.total:
                return JsonResponse({"error": "Refund exceeds the remaining sale amount"}, status=400)

            transaction_type = adjustment.adjustment_type
            FinancialTransaction.objects.create(
                transaction_id=f"{transaction_type.upper()}-{uuid.uuid4().hex[:20].upper()}",
                sale=sale,
                adjustment=adjustment,
                transaction_type=transaction_type,
                amount=adjustment.amount,
                method=sale.method,
                payment_reference=sale.payment_reference,
            )
            if transaction_type == "refund":
                for item in sale.items.prefetch_related("allocations").all():
                    for allocation in item.allocations.select_for_update().select_related("batch"):
                        batch = Batch.objects.select_for_update().get(pk=allocation.batch_id)
                        batch.quantity += allocation.quantity
                        batch.status = compute_batch_status(batch.expiry)
                        batch.save(update_fields=["quantity", "status"])
                        record_audit(
                            request.user,
                            "Restore Inventory",
                            batch.batch_number,
                            f"Refund {sale.transaction_id}; Quantity: {allocation.quantity}",
                        )
                refunded += adjustment.amount
                sale.state = "refunded" if refunded == sale.total else "partially-refunded"
                record_audit(
                    request.user,
                    "Execute Refund",
                    sale.transaction_id,
                    f"Amount: PHP {adjustment.amount:.2f}",
                )
            else:
                for item in sale.items.prefetch_related("allocations").all():
                    for allocation in item.allocations.select_for_update().select_related("batch"):
                        batch = Batch.objects.select_for_update().get(pk=allocation.batch_id)
                        batch.quantity += allocation.quantity
                        batch.status = compute_batch_status(batch.expiry)
                        batch.save(update_fields=["quantity", "status"])
                        record_audit(
                            request.user,
                            "Restore Inventory",
                            batch.batch_number,
                            f"Void {sale.transaction_id}; Quantity: {allocation.quantity}",
                        )
                sale.state = "voided"
                record_audit(
                    request.user,
                    "Execute Void",
                    sale.transaction_id,
                    f"Amount: PHP {adjustment.amount:.2f}",
                )
            sale.save(update_fields=["state"])
        adjustment.status = "approved"
        adjustment.approved_by = request.user
        adjustment.approved_at = timezone.now()
        adjustment.save(update_fields=["status", "approved_by", "approved_at"])
        record_audit(request.user, "Approve Sale Adjustment", adjustment.sale.transaction_id, f"Type: {adjustment.adjustment_type}; Amount: PHP {adjustment.amount:.2f}")
    return JsonResponse({"success": True, "adjustment_id": adjustment.pk, "status": adjustment.status})


@require_POST
@login_required(login_url="login")
@role_required("admin")
def reject_sale_adjustment_view(request, adjustment_id):
    with transaction.atomic():
        adjustment = get_object_or_404(SaleAdjustment.objects.select_for_update(), pk=adjustment_id)
        if adjustment.status != "pending":
            return JsonResponse({"error": "Adjustment is no longer pending"}, status=409)
        adjustment.status = "rejected"
        adjustment.rejected_by = request.user
        adjustment.rejected_at = timezone.now()
        adjustment.save(update_fields=["status", "rejected_by", "rejected_at"])
        record_audit(
            request.user,
            "Reject Sale Adjustment",
            adjustment.sale.transaction_id,
            f"Type: {adjustment.adjustment_type}; Amount: PHP {adjustment.amount:.2f}",
        )
    return JsonResponse({"success": True, "adjustment_id": adjustment.pk, "status": adjustment.status})


@login_required(login_url="login")
@role_required("admin", "pharmacist")
def reports_view(request):
    products = list(Product.objects.prefetch_related("batches").all())
    sales = SaleRecord.objects.prefetch_related("items").order_by("-created_at")
    period = request.GET.get("period", "today")
    today = date.today()
    if period == "week":
        sales = sales.filter(created_at__date__gte=today - timedelta(days=6))
    elif period == "month":
        sales = sales.filter(created_at__date__gte=today - timedelta(days=29))
    elif period == "quarter":
        sales = sales.filter(created_at__date__gte=today - timedelta(days=89))
    else:
        period = "today"
        sales = sales.filter(created_at__date=today)

    active_report = request.GET.get("report", "sales")
    returns = AuditEvent.objects.filter(action="Return Batch").select_related("actor")
    if period == "week":
        returns = returns.filter(created_at__date__gte=today - timedelta(days=6))
    elif period == "month":
        returns = returns.filter(created_at__date__gte=today - timedelta(days=29))
    elif period == "quarter":
        returns = returns.filter(created_at__date__gte=today - timedelta(days=89))
    else:
        returns = returns.filter(created_at__date=today)
    total_revenue = sum(float(s.total) for s in sales)
    avg_sale = total_revenue / sales.count() if sales.count() else 0
    expiring = []
    for p in products:
        active = list(p.batches.exclude(status="disposed"))
        if active:
            earliest_batch = min(active, key=lambda batch: batch.expiry)
            min_days = (earliest_batch.expiry - today).days
            if min_days <= 180:
                expiring.append({"product": p, "days": min_days, "expiry": earliest_batch.expiry})
    expiring.sort(key=lambda x: x["days"])
    low_stock = [p for p in products if 0 < p.stock <= p.reorder_level]
    out_of_stock = [p for p in products if p.stock == 0]

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="lakasahara-{active_report}-report.csv"'
        writer = csv.writer(response)
        if active_report == "sales":
            writer.writerow(["Transaction ID", "Date/Time", "Cashier", "Items", "Total", "Method"])
            for sale in sales:
                items = ", ".join(f"{item.product_name} x{item.qty}" for item in sale.items.all())
                cashier = sale.cashier.get_full_name() if sale.cashier else ""
                writer.writerow([sale.transaction_id, sale.created_at.strftime("%Y-%m-%d %H:%M"), cashier, items, sale.total, sale.method])
        elif active_report == "inventory":
            writer.writerow(["Product", "Category", "Type", "Stock", "Reorder At", "Unit Price", "Status"])
            for product in products:
                writer.writerow([product.name, product.category, product.type, product.stock, product.reorder_level, product.price, product.stock_label[0]])
        elif active_report == "expiry":
            writer.writerow(["Product", "Type", "Expiry", "Days Left", "Stock"])
            for row in expiring:
                writer.writerow([row["product"].name, row["product"].type, row["expiry"], row["days"], row["product"].stock])
        elif active_report == "reorder":
            writer.writerow(["Product", "Category", "Type", "Stock", "Reorder At", "Status"])
            for product in out_of_stock + low_stock:
                writer.writerow([product.name, product.category, product.type, product.stock, product.reorder_level, product.stock_label[0]])
        elif active_report == "returns":
            writer.writerow(["Date/Time", "Batch No.", "Authorized By", "Details"])
            for event in returns:
                authorized_by = event.actor.get_full_name() if event.actor else ""
                writer.writerow([event.created_at.strftime("%Y-%m-%d %H:%M"), event.target, authorized_by, event.detail])
        return response

    return render(
        request,
        "reports.html",
        {
            "role": get_role(request),
            "products": products,
            "sales": sales,
            "total_revenue": total_revenue,
            "avg_sale": avg_sale,
            "expiring": expiring,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "returns": returns,
            "active_report": active_report,
            "period": period,
        },
    )


@login_required(login_url="login")
@role_required("admin", "pharmacist")
def expiry_view(request):
    today = date.today()
    all_rows = []
    for p in Product.objects.prefetch_related("batches").all():
        for b in p.batches.exclude(status="disposed"):
            days = (b.expiry - today).days
            if days <= 365:
                all_rows.append(
                    {
                        "product": p,
                        "batch": b,
                        "days": days,
                        "is_expired": days < 0,
                        "is_critical": 0 <= days <= 90,
                    }
                )
    all_rows.sort(key=lambda x: x["days"])
    f = request.GET.get("filter", "all")
    if f == "expired":
        rows = [r for r in all_rows if r["is_expired"]]
    elif f == "critical":
        rows = [r for r in all_rows if not r["is_expired"] and r["days"] <= 90]
    elif f == "warning":
        rows = [r for r in all_rows if 90 < r["days"] <= 180]
    else:
        rows = all_rows
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="lakasahara-expiry-{f}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Product", "Kind", "Batch No.", "Type", "Expiry", "Days Left", "Quantity", "Shelf", "Risk"])
        for row in rows:
            risk = "Expired" if row["is_expired"] else "Critical" if row["is_critical"] else "Warning"
            days_left = "Expired" if row["is_expired"] else row["days"]
            writer.writerow([row["product"].name, row["product"].kind, row["batch"].batch_number, row["product"].type, row["batch"].expiry, days_left, row["batch"].quantity, row["batch"].shelf, risk])
        return response

    return render(
        request,
        "expiry.html",
        {
            "role": get_role(request),
            "rows": rows,
            "filter_type": f,
            "expired_count": sum(1 for r in all_rows if r["is_expired"]),
            "critical_count": sum(
                1 for r in all_rows if not r["is_expired"] and r["days"] <= 90
            ),
            "warning_count": sum(1 for r in all_rows if 90 < r["days"] <= 180),
        },
    )
