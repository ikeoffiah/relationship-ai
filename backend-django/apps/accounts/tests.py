from django.test import TestCase
from django.apps import apps


class AccountsConfigTest(TestCase):
    def test_apps_config(self):
        self.assertEqual(apps.get_app_config("accounts").name, "apps.accounts")
