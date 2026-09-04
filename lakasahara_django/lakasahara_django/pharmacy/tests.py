import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import close_old_connections
from django.test import RequestFactory, TestCase, TransactionTestCase

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
    UserProfile,
)


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


class XssOutputEncodingTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="xss_admin", password="StrongPass123!")
        UserProfile.objects.create(user=self.admin, role="admin")
        self.pharmacist = User.objects.create_user(username="xss_pharmacist", password="StrongPass123!")
        UserProfile.objects.create(user=self.pharmacist, role="pharmacist")
        self.staff = User.objects.create_user(username="xss_staff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff, role="staff")
        self.payload = '<script>window.__xss_executed__=true</script>'
        supplier = Supplier.objects.create(name=self.payload)
        product = Product.objects.create(
            name=self.payload,
            barcode="XSS-001",
            category="Medicine",
            kind=self.payload,
            type="OTC",
            price=10,
            reorder_level=1,
            shelf=self.payload,
            supplier=supplier,
        )
        Batch.objects.create(
            product=product,
            batch_number=self.payload,
            expiry=date(2030, 12, 31),
            quantity=2,
            supplier_name=self.payload,
            shelf=self.payload,
        )

    def test_user_controlled_values_are_encoded_on_all_role_surfaces(self):
        requests = [
            (self.admin, "/products/"),
            (self.admin, "/dashboard/admin/"),
            (self.admin, "/reports/?report=inventory"),
            (self.pharmacist, "/inventory/"),
            (self.pharmacist, "/dashboard/pharmacist/"),
            (self.pharmacist, "/expiry/"),
            (self.pharmacist, "/reports/?report=inventory"),
            (self.staff, "/sales/"),
            (self.staff, "/dashboard/staff/"),
        ]

        for user, path in requests:
            self.client.force_login(user)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn(self.payload, response.content.decode("utf-8"))


class ProductEditFormJsonTest(TestCase):
    def test_edit_form_returns_json_for_decimal_field_values(self):
        user = User.objects.create_user(username="edit_form_admin", password="StrongPass123!")
        UserProfile.objects.create(user=user, role="admin")
        supplier = Supplier.objects.create(name="Edit Form Supplier")
        product = Product.objects.create(
            name="Edit Form Product",
            barcode="EDIT-001",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price="9.25",
            reorder_level=1,
            shelf="A1",
            supplier=supplier,
        )

        self.client.force_login(user)
        response = self.client.get(
            f"/products/{product.pk}/edit-form/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        fields = {field["name"]: field for field in response.json()["fields"]}
        self.assertEqual(fields["price"]["value"], "9.25")


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


class PostgreSQLConcurrencyTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = User.objects.create_user(
            username="postgres_concurrency_staff", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.user, role="staff")
        supplier = Supplier.objects.create(name="Concurrency Supplier")
        self.product = Product.objects.create(
            name="Concurrency Product",
            barcode="CONC-001",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=1,
            shelf="A1",
            supplier=supplier,
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number="CONC-B1",
            expiry=date(2030, 12, 31),
            quantity=1,
            supplier_name=supplier.name,
            shelf="A1",
        )

    def _run_simultaneously(self, operation):
        barrier = Barrier(2)

        def worker(worker_index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation(worker_index)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            return [future.result(timeout=30) for future in futures]

    def _checkout(self, idempotency_key):
        request = self.request_factory.post(
            "/sales/checkout/",
            data=json.dumps(
                {
                    "idempotency_key": idempotency_key,
                    "cart": [{"id": self.product.pk, "qty": 1}],
                    "cash_given": 10,
                }
            ),
            content_type="application/json",
        )
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        from .views import checkout_view

        return checkout_view(request)

    def test_concurrent_last_stock_checkout_allows_exactly_one_sale(self):
        responses = self._run_simultaneously(
            lambda index: self._checkout(f"concurrent-last-stock-{index}")
        )

        statuses = sorted(response.status_code for response in responses)
        self.batch.refresh_from_db()
        self.assertEqual(
            statuses,
            [200, 400],
            [(response.status_code, response.content.decode()) for response in responses],
        )
        self.assertEqual(self.batch.quantity, 0)
        self.assertGreaterEqual(self.batch.quantity, 0)
        self.assertEqual(SaleRecord.objects.count(), 1)

    def test_concurrent_identical_idempotency_key_returns_one_original_sale(self):
        responses = self._run_simultaneously(
            lambda index: self._checkout("concurrent-identical-key")
        )

        payloads = [json.loads(response.content) for response in responses]
        self.assertTrue(
            all(response.status_code == 200 for response in responses),
            [(response.status_code, response.content.decode()) for response in responses],
        )
        self.assertEqual(
            {payload["transaction_id"] for payload in payloads},
            {SaleRecord.objects.get().transaction_id},
        )
        self.assertCountEqual(
            [payload["duplicate"] for payload in payloads], [False, True]
        )
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 0)
        self.assertEqual(SaleRecord.objects.count(), 1)

    def test_concurrent_disposal_serializes_and_preserves_nonnegative_quantity(self):
        pharmacist = User.objects.create_user(
            username="postgres_concurrency_pharmacist", password="StrongPass123!"
        )
        UserProfile.objects.create(user=pharmacist, role="pharmacist")

        def dispose(_index):
            request = self.request_factory.post(
                f"/inventory/batch/{self.batch.pk}/dispose/",
                {"qty": 1, "reason": "Expired", "authorized_by": "Pharmacist"},
            )
            request.user = pharmacist
            request.session = {}
            request._messages = FallbackStorage(request)
            from .views import dispose_batch_view

            return dispose_batch_view(request, self.batch.pk)

        responses = self._run_simultaneously(dispose)

        self.batch.refresh_from_db()
        self.assertEqual(
            sorted(response.status_code for response in responses), [200, 302]
        )
        self.assertEqual(self.batch.quantity, 0)
        self.assertGreaterEqual(self.batch.quantity, 0)
        self.assertEqual(self.batch.disposed_qty, 1)
        self.assertEqual(AuditEvent.objects.filter(action="Dispose Batch").count(), 1)


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


class FinancialWorkflowTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.staff = User.objects.create_user(username="workflow_staff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff, role="staff")
        self.admin = User.objects.create_user(username="workflow_admin", password="StrongPass123!")
        UserProfile.objects.create(user=self.admin, role="admin")
        supplier = Supplier.objects.create(name="Workflow Supplier")
        product = Product.objects.create(
            name="Workflow Product",
            barcode="WORKFLOW-001",
            category="Medicine",
            kind="Tablet",
            type="OTC",
            price=10,
            reorder_level=1,
            shelf="A1",
            supplier=supplier,
        )
        self.batch = Batch.objects.create(
            product=product,
            batch_number="WORKFLOW-B1",
            expiry=date(2030, 12, 31),
            quantity=3,
            supplier_name=supplier.name,
            shelf="A1",
        )
        self.sale = SaleRecord.objects.create(
            transaction_id="TXN-WORKFLOW",
            subtotal=20,
            total=20,
            cash_given=20,
            cashier=self.staff,
        )
        FinancialTransaction.objects.create(
            transaction_id="TXN-WORKFLOW",
            sale=self.sale,
            transaction_type="sale",
            amount=20,
            method="cash",
        )
        sale_item = SaleItem.objects.create(
            sale=self.sale,
            product=product,
            product_name=product.name,
            qty=2,
            price=10,
        )
        SaleItemAllocation.objects.create(sale_item=sale_item, batch=self.batch, quantity=2)
        self.batch.quantity = 1
        self.batch.save(update_fields=["quantity", "status"])

    def _request_adjustment(self, adjustment_type, amount):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/sales/adjustments/request/",
            data=json.dumps(
                {
                    "sale_id": self.sale.pk,
                    "adjustment_type": adjustment_type,
                    "amount": str(amount),
                    "reason": "Customer request",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        return SaleAdjustment.objects.get(pk=response.json()["adjustment_id"])

    def _approve(self, adjustment):
        self.client.force_login(self.admin)
        return self.client.post(f"/sales/adjustments/{adjustment.pk}/approve/")

    def test_pending_refund_request(self):
        adjustment = self._request_adjustment("refund", 10)

        self.assertEqual(adjustment.status, "pending")
        self.assertTrue(AuditEvent.objects.filter(action="Request Sale Adjustment").exists())

    def test_pending_void_request(self):
        adjustment = self._request_adjustment("void", 20)

        self.assertEqual(adjustment.status, "pending")

    def test_admin_approval_executes_refund_and_restores_inventory(self):
        adjustment = self._request_adjustment("refund", 20)
        response = self._approve(adjustment)

        self.assertEqual(response.status_code, 200)
        adjustment.refresh_from_db()
        self.sale.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(adjustment.status, "approved")
        self.assertEqual(self.sale.state, "refunded")
        self.assertEqual(self.sale.total, 20)
        self.assertEqual(self.batch.quantity, 3)
        self.assertEqual(
            list(FinancialTransaction.objects.filter(sale=self.sale).values_list("transaction_type", flat=True)),
            ["sale", "refund"],
        )
        self.assertTrue(AuditEvent.objects.filter(action="Approve Sale Adjustment").exists())
        self.assertTrue(AuditEvent.objects.filter(action="Execute Refund").exists())
        self.assertTrue(AuditEvent.objects.filter(action="Restore Inventory").exists())

    def test_admin_rejection_keeps_sale_and_inventory_unchanged(self):
        adjustment = self._request_adjustment("refund", 10)
        self.client.force_login(self.admin)
        response = self.client.post(f"/sales/adjustments/{adjustment.pk}/reject/")

        self.assertEqual(response.status_code, 200)
        adjustment.refresh_from_db()
        self.sale.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(adjustment.status, "rejected")
        self.assertEqual(self.sale.state, "completed")
        self.assertEqual(self.batch.quantity, 1)
        self.assertEqual(FinancialTransaction.objects.filter(sale=self.sale).count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="Reject Sale Adjustment").exists())

    def test_void_executes_reversal_and_updates_sale_state(self):
        adjustment = self._request_adjustment("void", 20)
        response = self._approve(adjustment)

        self.assertEqual(response.status_code, 200)
        self.sale.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(self.sale.state, "voided")
        self.assertEqual(self.sale.total, 20)
        self.assertEqual(self.batch.quantity, 3)
        self.assertTrue(FinancialTransaction.objects.filter(sale=self.sale, transaction_type="void", amount=20).exists())
        self.assertTrue(AuditEvent.objects.filter(action="Execute Void").exists())

    def test_refund_greater_than_sale_total_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/sales/adjustments/request/",
            data=json.dumps({"sale_id": self.sale.pk, "adjustment_type": "refund", "amount": "21", "reason": "Too much"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SaleAdjustment.objects.exists())

    def test_duplicate_refund_is_rejected_without_second_transaction(self):
        first = self._request_adjustment("refund", 20)
        self.assertEqual(self._approve(first).status_code, 200)
        second = self._request_adjustment("refund", 1)

        response = self._approve(second)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FinancialTransaction.objects.filter(sale=self.sale, transaction_type="refund").count(), 1)
        self.assertEqual(SaleAdjustment.objects.get(pk=second.pk).status, "pending")

    def test_concurrent_duplicate_approval_executes_adjustment_once(self):
        adjustment = self._request_adjustment("refund", 10)
        barrier = Barrier(2)

        def approve():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                request = RequestFactory().post(f"/sales/adjustments/{adjustment.pk}/approve/")
                request.user = self.admin
                from .views import approve_sale_adjustment_view

                return approve_sale_adjustment_view(request, adjustment.pk)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = [executor.submit(approve) for _ in range(2)]
            responses = [future.result(timeout=30) for future in responses]

        self.assertEqual(sorted(response.status_code for response in responses), [200, 409])
        self.assertEqual(FinancialTransaction.objects.filter(sale=self.sale, transaction_type="refund").count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action="Execute Refund").count(), 1)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 3)
