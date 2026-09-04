import json
import re
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from .models import AuditEvent, Product, SaleAdjustment, SaleRecord, Supplier, UserProfile, Batch


class SalesPageJsonTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff_pos_owner", password="staff123")
        UserProfile.objects.create(user=self.user, role="staff")

        supplier = Supplier.objects.create(name="Acme Pharma")
        product = Product.objects.create(
            name="Paracetamol",
            barcode="ABC123",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=5,
            shelf="A1",
            supplier=supplier,
        )
        Batch.objects.create(
            product=product,
            batch_number="B1",
            expiry=date(2030, 12, 31),
            quantity=15,
            supplier_name=supplier.name,
            shelf="A1",
        )

    def test_sales_page_embeds_valid_json_for_pos(self):
        self.client.force_login(self.user)
        response = self.client.get("/sales/")

        self.assertEqual(response.status_code, 200)
        match = re.search(
            r'<script id="products-data" type="application/json">(.*)</script>',
            response.content.decode("utf-8"),
            re.S,
        )
        self.assertIsNotNone(
            match, "Sales page should include the products JSON script tag."
        )
        payload = match.group(1)
        parsed = json.loads(json.loads(payload))
        self.assertIsInstance(parsed, list)
        self.assertTrue(parsed)


class StaffDashboardProductModalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="staff123")
        UserProfile.objects.create(user=self.user, role="staff")
        supplier = Supplier.objects.create(name="Acme Pharma")
        Product.objects.create(
            name="Paracetamol",
            barcode="ABC123",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=5,
            shelf="A1",
            supplier=supplier,
        )

    def test_staff_dashboard_includes_product_modal(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/staff/")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('id="product-modal"', html)
        self.assertIn('data-product-name="Paracetamol"', html)


class AccessControlTest(TestCase):
    def test_user_without_profile_is_redirected_from_dashboard(self):
        user = User.objects.create_user(username="no_profile", password="secret123")
        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/login/")


class AdminPosAccessTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_pos", password="StrongPass123!")
        UserProfile.objects.create(user=self.admin, role="admin")

    def test_admin_cannot_access_sales_pos(self):
        self.client.force_login(self.admin)

        response = self.client.get("/sales/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, "/dashboard/admin/")

    def test_admin_nav_does_not_show_sales_pos(self):
        self.client.force_login(self.admin)

        response = self.client.get("/dashboard/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sales POS")


class LoginSecurityTest(TestCase):
    def test_login_blocks_after_five_failed_attempts(self):
        User.objects.create_user(username="lockeduser", password="StrongPass123!")

        for _ in range(5):
            response = self.client.post(
                "/login/",
                {"username": "lockeduser", "password": "wrong-password"},
                follow=True,
            )

        self.assertContains(response, "Too many failed login attempts")
        self.assertNotIn("_auth_user_id", self.client.session)


class AdminUserDeleteTest(TestCase):
    def test_admin_can_delete_non_self_user(self):
        admin = User.objects.create_user(username="admin_delete", password="StrongPass123!")
        UserProfile.objects.create(user=admin, role="admin")
        target = User.objects.create_user(username="staff_delete", password="StrongPass123!")
        UserProfile.objects.create(user=target, role="staff")

        self.client.force_login(admin)
        response = self.client.post(
            "/dashboard/admin/",
            {"action": "delete_user", "user_id": target.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())


class GCashCheckoutTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cashier", password="StrongPass123!")
        UserProfile.objects.create(user=self.user, role="staff")
        supplier = Supplier.objects.create(name="GCash Supplier")
        self.product = Product.objects.create(
            name="GCash Test Product",
            barcode="GCASH-001",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=2,
            shelf="A1",
            supplier=supplier,
        )
        Batch.objects.create(
            product=self.product,
            batch_number="GCASH-B1",
            expiry=date(2030, 12, 31),
            quantity=5,
            supplier_name=supplier.name,
            shelf="A1",
        )

    def test_gcash_requires_reference_number(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/sales/checkout/",
            data=json.dumps({"idempotency_key": "gcash-required", "cart": [{"id": self.product.pk, "name": self.product.name, "price": 10, "qty": 1}], "method": "gcash"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("reference number", response.json()["error"])

    def test_gcash_rejects_non_numeric_reference_number(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/sales/checkout/",
            data=json.dumps({"idempotency_key": "gcash-invalid", "cart": [{"id": self.product.pk, "name": self.product.name, "price": 10, "qty": 1}], "method": "gcash", "payment_reference": "REF-123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("digits only", response.json()["error"])

    def test_gcash_reference_is_saved_for_receipt(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/sales/checkout/",
            data=json.dumps({"idempotency_key": "gcash-valid", "cart": [{"id": self.product.pk, "name": self.product.name, "price": 10, "qty": 1}], "method": "gcash", "payment_reference": "12345"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payment_reference"], "12345")

    def test_checkout_uses_database_price_and_rejects_overselling(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/sales/checkout/",
            data=json.dumps({"idempotency_key": "price-check", "cart": [{"id": self.product.pk, "name": "Fake", "price": 0.01, "qty": 1}], "cash_given": 10}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subtotal"], 10.0)
        self.assertEqual(response.json()["items"][0]["name"], self.product.name)
        self.assertEqual(response.json()["items"][0]["price"], 10.0)

        response = self.client.post(
            "/sales/checkout/",
            data=json.dumps({"idempotency_key": "oversell-check", "cart": [{"id": self.product.pk, "qty": 99}]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_replayed_checkout_returns_original_sale(self):
        self.client.force_login(self.user)
        payload = {"idempotency_key": "replay-check", "cart": [{"id": self.product.pk, "qty": 1}], "cash_given": 10}
        first = self.client.post("/sales/checkout/", data=json.dumps(payload), content_type="application/json")
        second = self.client.post("/sales/checkout/", data=json.dumps(payload), content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(first.json()["transaction_id"], second.json()["transaction_id"])


class InventoryMutationSecurityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pharmacist_mutation", password="StrongPass123!")
        UserProfile.objects.create(user=self.user, role="pharmacist")
        supplier = Supplier.objects.create(name="Mutation Supplier")
        product = Product.objects.create(
            name="Mutation Product",
            barcode="MUT-001",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=2,
            shelf="A1",
            supplier=supplier,
        )
        self.batch = Batch.objects.create(
            product=product,
            batch_number="MUT-B1",
            expiry=date(2025, 1, 1),
            quantity=5,
            supplier_name=supplier.name,
            shelf="A1",
        )

    def test_disposal_cannot_exceed_available_quantity(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f"/inventory/batch/{self.batch.pk}/dispose/",
            {"qty": 6, "reason": "Expired", "authorized_by": "Pharmacist"},
        )

        self.assertEqual(response.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 5)
        self.assertFalse(AuditEvent.objects.filter(action="Dispose Batch").exists())

    def test_return_cannot_be_repeated(self):
        self.client.force_login(self.user)
        payload = {"reason": "Expired"}
        first = self.client.post(f"/inventory/batch/{self.batch.pk}/return/", payload)
        self.batch.refresh_from_db()
        quantity_after_first = self.batch.disposed_qty
        second = self.client.post(f"/inventory/batch/{self.batch.pk}/return/", payload)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(self.batch.quantity, 0)
        self.assertEqual(self.batch.disposed_qty, quantity_after_first)
        self.assertEqual(AuditEvent.objects.filter(action="Return Batch").count(), 1)


class SaleAdjustmentSecurityTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="adjustment_staff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff, role="staff")
        self.admin = User.objects.create_user(username="adjustment_admin", password="StrongPass123!")
        UserProfile.objects.create(user=self.admin, role="admin")
        self.sale = SaleRecord.objects.create(transaction_id="TXN-ADJUSTMENT", total=100, subtotal=100, cash_given=100, cashier=self.staff)

    def test_staff_can_request_but_not_approve_adjustment(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/sales/adjustments/request/",
            data=json.dumps({"sale_id": self.sale.pk, "adjustment_type": "refund", "amount": "10", "reason": "Customer return"}),
            content_type="application/json",
        )
        adjustment = SaleAdjustment.objects.get()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(adjustment.status, "pending")

        response = self.client.post(f"/sales/adjustments/{adjustment.pk}/approve/")
        self.assertEqual(response.status_code, 302)
        adjustment.refresh_from_db()
        self.assertEqual(adjustment.status, "pending")

    def test_admin_can_approve_adjustment_without_editing_sale(self):
        adjustment = SaleAdjustment.objects.create(
            sale=self.sale,
            adjustment_type="void",
            amount=100,
            reason="Duplicate sale",
            requested_by=self.staff,
        )
        self.client.force_login(self.admin)
        response = self.client.post(f"/sales/adjustments/{adjustment.pk}/approve/")

        self.assertEqual(response.status_code, 200)
        adjustment.refresh_from_db()
        self.sale.refresh_from_db()
        self.assertEqual(adjustment.status, "approved")
        self.assertEqual(self.sale.total, 100)
