import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SECRET = "test-only-production-secret-9f2e7d4c6b8a1f3e5d7c9b2a4e6f8d1c"


class ProductionSettingsTest(SimpleTestCase):
    def run_production_check(self, **overrides):
        environment = os.environ.copy()
        for name in list(environment):
            if name.startswith("DJANGO_"):
                environment.pop(name)
        environment.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_SECRET_KEY": TEST_SECRET,
                "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
                "DJANGO_DEBUG": "False",
                "DJANGO_SECURE_SSL_REDIRECT": "True",
                "DJANGO_SESSION_COOKIE_SECURE": "True",
                "DJANGO_CSRF_COOKIE_SECURE": "True",
                "DJANGO_SECURE_HSTS_SECONDS": "31536000",
                "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "True",
                "DJANGO_SECURE_HSTS_PRELOAD": "True",
            }
        )
        for name, value in overrides.items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        return subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

    def assertProductionStartupFails(self, **overrides):
        result = self.run_production_check(**overrides)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_production_secret_key_fails(self):
        self.assertProductionStartupFails(DJANGO_SECRET_KEY=None)

    def test_insecure_production_debug_cannot_be_enabled(self):
        self.assertProductionStartupFails(DJANGO_DEBUG="True")

    def test_insecure_ssl_redirect_cannot_be_disabled(self):
        self.assertProductionStartupFails(DJANGO_SECURE_SSL_REDIRECT="False")

    def test_secure_session_cookie_cannot_be_disabled(self):
        self.assertProductionStartupFails(DJANGO_SESSION_COOKIE_SECURE="False")

    def test_secure_csrf_cookie_cannot_be_disabled(self):
        self.assertProductionStartupFails(DJANGO_CSRF_COOKIE_SECURE="False")

    def test_production_hosts_are_required(self):
        self.assertProductionStartupFails(DJANGO_ALLOWED_HOSTS=None)

    def test_valid_production_configuration_passes(self):
        result = self.run_production_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("System check identified no issues", result.stdout)