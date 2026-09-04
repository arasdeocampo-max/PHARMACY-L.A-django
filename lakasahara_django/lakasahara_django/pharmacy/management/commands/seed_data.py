from datetime import datetime
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from pharmacy.models import Batch, Product, Supplier, UserProfile, compute_batch_status

IMG = lambda uid: f"https://images.unsplash.com/{uid}?w=120&h=120&fit=crop&auto=format"
IMAGES = {
    "capsule": IMG("photo-1628771065518-0d82f1938462"),
    "tablet": IMG("photo-1573883430697-4c3479aae6b9"),
    "blister": IMG("photo-1584308666744-24d5c474f2ae"),
    "pillBlue": IMG("photo-1607619056574-7b8d3ee536b2"),
    "pillPink": IMG("photo-1581159186721-b68b78da4ec9"),
    "syrup": IMG("photo-1635166304271-04931640a450"),
    "cream": IMG("photo-1712168044214-f5a272c23a5b"),
    "vial": IMG("photo-1562243061-204550d8a2c9"),
    "gloves": IMG("photo-1585421514738-01798e348b17"),
    "mask": IMG("photo-1584819762556-68601d7f3a86"),
    "assorted": IMG("photo-1471864190281-a93a3070b6de"),
    "white": IMG("photo-1588718889344-f7bd7a565d20"),
}
USERS = [
    ("admin", "admin123", "Maria", "Santos", "admin"),
    ("pharmacist", "pharma123", "Jose", "Reyes", "pharmacist"),
    ("staff", "staff123", "Ana", "Cruz", "staff"),
]
SUPPLIERS = {
    "MedPharm Inc.": ("+63 2 8888 1100", "orders@medpharm.ph", "Net 30", 3),
    "Generic Labs": ("+63 2 8555 2200", "sales@genericlabs.ph", "Net 15", 2),
    "AllerCare PH": ("+63 2 8333 4400", "supply@allercare.ph", "Net 30", 5),
    "CardioPharma": ("+63 2 8777 5500", "orders@cardiopharma.ph", "Net 45", 4),
    "DiabeCare PH": ("+63 2 8444 6600", "ops@diabecare.ph", "Net 30", 3),
    "RespiMed Co.": ("+63 2 8222 7700", "sales@respimed.ph", "Net 15", 2),
    "VitaBoost PH": ("+63 2 8111 8800", "orders@vitaboost.ph", "Net 30", 2),
    "DermaCare PH": ("+63 2 8999 9900", "supply@dermacare.ph", "Net 30", 4),
    "InsuLife Corp": ("+63 2 8666 0011", "cold@insulife.ph", "Net 60", 7),
    "SafeSupply PH": ("+63 2 8123 4567", "bulk@safesupply.ph", "Net 30", 3),
    "GastroMed PH": ("+63 2 8321 6543", "orders@gastromed.ph", "Net 15", 3),
    "PainAway Inc.": ("+63 2 8765 4321", "sales@painaway.ph", "Net 30", 2),
}
PRODUCTS = [
    (
        "Amoxicillin 500mg",
        "MED-001",
        "Medicine",
        "Capsule",
        "RX",
        12.50,
        50,
        "A1",
        "MedPharm Inc.",
        "capsule",
    ),
    (
        "Paracetamol 500mg",
        "MED-002",
        "Medicine",
        "Tablet",
        "OTC",
        5.00,
        30,
        "A2",
        "Generic Labs",
        "tablet",
    ),
    (
        "Cetirizine 10mg",
        "MED-003",
        "Medicine",
        "Tablet",
        "OTC",
        8.75,
        20,
        "B1",
        "AllerCare PH",
        "blister",
    ),
    (
        "Losartan 50mg",
        "MED-004",
        "Medicine",
        "Tablet",
        "RX",
        15.00,
        30,
        "C2",
        "CardioPharma",
        "pillPink",
    ),
    (
        "Metformin 500mg",
        "MED-005",
        "Medicine",
        "Tablet",
        "RX",
        9.25,
        40,
        "C3",
        "DiabeCare PH",
        "pillBlue",
    ),
    (
        "Salbutamol Syrup",
        "MED-006",
        "Medicine",
        "Syrup",
        "RX",
        48.00,
        15,
        "D1",
        "RespiMed Co.",
        "syrup",
    ),
    (
        "Vitamin C 500mg",
        "MED-007",
        "Medicine",
        "Tablet",
        "OTC",
        6.00,
        60,
        "E1",
        "VitaBoost PH",
        "assorted",
    ),
    (
        "Betamethasone Cream",
        "MED-008",
        "Medicine",
        "Cream",
        "RX",
        65.00,
        10,
        "F2",
        "DermaCare PH",
        "cream",
    ),
    (
        "Insulin Glargine 100u",
        "MED-009",
        "Medicine",
        "Vial",
        "RX",
        895.00,
        5,
        "G1",
        "InsuLife Corp",
        "vial",
    ),
    (
        "Surgical Gloves L",
        "SUP-001",
        "Medical Supply",
        "Medical Supply",
        "OTC",
        15.00,
        50,
        "H1",
        "SafeSupply PH",
        "gloves",
    ),
    (
        "Omeprazole 20mg",
        "MED-011",
        "Medicine",
        "Capsule",
        "OTC",
        11.00,
        25,
        "A3",
        "GastroMed PH",
        "capsule",
    ),
    (
        "Ibuprofen 400mg",
        "MED-012",
        "Medicine",
        "Tablet",
        "OTC",
        7.50,
        40,
        "A4",
        "PainAway Inc.",
        "white",
    ),
    (
        "Cotrimoxazole 480mg",
        "MED-013",
        "Medicine",
        "Tablet",
        "RX",
        6.50,
        30,
        "B2",
        "MedPharm Inc.",
        "blister",
    ),
    (
        "N95 Mask (Box/25)",
        "SUP-002",
        "Medical Supply",
        "Medical Supply",
        "OTC",
        350.00,
        10,
        "H2",
        "SafeSupply PH",
        "mask",
    ),
    (
        "Amlodipine 5mg",
        "MED-015",
        "Medicine",
        "Tablet",
        "RX",
        8.00,
        40,
        "C1",
        "CardioPharma",
        "pillPink",
    ),
]
BATCHES = [
    ("MED-001", "AMX-B001", "2026-08-10", 100, "MedPharm Inc.", "A1", "2025-10-01"),
    ("MED-001", "AMX-B002", "2026-12-20", 80, "MedPharm Inc.", "A1", "2026-01-15"),
    ("MED-001", "AMX-B003", "2027-03-10", 60, "MedPharm Inc.", "A1", "2026-04-01"),
    ("MED-002", "PAR-B001", "2025-03-20", 10, "Generic Labs", "A2", "2024-08-10"),
    ("MED-002", "PAR-B002", "2026-09-15", 8, "Generic Labs", "A2", "2026-03-01"),
    ("MED-003", "CET-B001", "2026-10-15", 40, "AllerCare PH", "B1", "2025-12-01"),
    ("MED-003", "CET-B002", "2026-11-30", 45, "AllerCare PH", "B1", "2026-02-01"),
    ("MED-004", "LOS-B001", "2025-07-10", 6, "CardioPharma", "C2", "2024-11-01"),
    ("MED-005", "MET-B001", "2026-11-15", 80, "DiabeCare PH", "C3", "2026-01-10"),
    ("MED-005", "MET-B002", "2027-02-28", 50, "DiabeCare PH", "C3", "2026-05-01"),
    ("MED-006", "SAL-B001", "2025-05-15", 32, "RespiMed Co.", "D1", "2024-09-01"),
    ("MED-007", "VTC-B001", "2027-01-15", 150, "VitaBoost PH", "E1", "2026-01-01"),
    ("MED-007", "VTC-B002", "2027-05-20", 100, "VitaBoost PH", "E1", "2026-03-01"),
    ("MED-007", "VTC-B003", "2027-09-01", 60, "VitaBoost PH", "E1", "2026-06-01"),
    ("MED-008", "BET-B001", "2026-06-30", 12, "DermaCare PH", "F2", "2025-08-01"),
    ("MED-008", "BET-B002", "2027-01-15", 10, "DermaCare PH", "F2", "2026-04-01"),
    ("MED-009", "INS-B001", "2025-01-31", 8, "InsuLife Corp", "G1", "2024-06-01"),
    ("SUP-001", "GLV-B001", "2028-06-30", 100, "SafeSupply PH", "H1", "2025-06-01"),
    ("SUP-001", "GLV-B002", "2028-12-31", 44, "SafeSupply PH", "H1", "2026-01-01"),
    ("MED-011", "OMP-B001", "2026-09-15", 50, "GastroMed PH", "A3", "2025-11-01"),
    ("MED-011", "OMP-B002", "2027-03-20", 42, "GastroMed PH", "A3", "2026-04-01"),
    ("MED-012", "IBU-B001", "2026-04-20", 0, "PainAway Inc.", "A4", "2025-07-01"),
    ("MED-013", "COT-B001", "2025-02-28", 40, "MedPharm Inc.", "B2", "2024-06-01"),
    ("MED-013", "COT-B002", "2026-10-30", 27, "MedPharm Inc.", "B2", "2026-01-01"),
    ("SUP-002", "MSK-B001", "2028-06-30", 8, "SafeSupply PH", "H2", "2025-08-01"),
    ("SUP-002", "MSK-B002", "2029-01-01", 12, "SafeSupply PH", "H2", "2026-02-01"),
    ("MED-015", "AML-B001", "2026-09-25", 100, "CardioPharma", "C1", "2025-11-01"),
    ("MED-015", "AML-B002", "2027-03-31", 78, "CardioPharma", "C1", "2026-03-01"),
]


class Command(BaseCommand):
    help = "Seeds the database with sample Lakasahara pharmacy data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding users..."))
        for username, password, first, last, role in USERS:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.first_name = first
            user.last_name = last
            user.save()
            UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding suppliers..."))
        suppliers = {}
        for name, (phone, email, terms, lead) in SUPPLIERS.items():
            s, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    "phone": phone,
                    "email": email,
                    "payment_terms": terms,
                    "lead_days": lead,
                },
            )
            suppliers[name] = s
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding products..."))
        products = {}
        for (
            name,
            barcode,
            cat,
            kind,
            ptype,
            price,
            reorder,
            shelf,
            sup_name,
            img_key,
        ) in PRODUCTS:
            p, _ = Product.objects.get_or_create(
                barcode=barcode,
                defaults={
                    "name": name,
                    "category": cat,
                    "kind": kind,
                    "type": ptype,
                    "price": price,
                    "reorder_level": reorder,
                    "shelf": shelf,
                    "supplier": suppliers[sup_name],
                    "image_url": IMAGES[img_key],
                },
            )
            products[barcode] = p
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding batches..."))
        for barcode, batch_no, expiry_str, qty, sup, shelf, recv in BATCHES:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            received = datetime.strptime(recv, "%Y-%m-%d").date()
            Batch.objects.get_or_create(
                product=products[barcode],
                batch_number=batch_no,
                defaults={
                    "expiry": expiry,
                    "quantity": qty,
                    "supplier_name": sup,
                    "shelf": shelf,
                    "received_date": received,
                    "status": compute_batch_status(expiry),
                },
            )
        self.stdout.write(self.style.SUCCESS("\n✅  Seed complete!"))
        for u, pw, *_ in USERS:
            self.stdout.write(f"  {u} / {pw}")
