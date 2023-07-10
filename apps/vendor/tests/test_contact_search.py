from unittest.mock import patch

from ddt import data, ddt, unpack
from django.test import TestCase
from organizations.models import Organization

from apps.administrator.tasks import fetch_weekly_ofac_list
from apps.vendor.models import Contact, ContactRole, Vendor
from apps.vendor.tasks import contact_search

from .tests import (
    _mock_download_ofac_address_file,
    _mock_download_ofac_alternate_file,
    _mock_download_ofac_sdn_file,
)


@ddt
class TestContactSearch(TestCase):
    vendor: Vendor

    @classmethod
    @patch("apps.administrator.tasks.download_ofac_sdn_file", _mock_download_ofac_sdn_file)
    @patch("apps.administrator.tasks.download_ofac_alternate_file", _mock_download_ofac_alternate_file)
    @patch("apps.administrator.tasks.download_ofac_address_file", _mock_download_ofac_address_file)
    def setUpTestData(cls):
        fetch_weekly_ofac_list()
        org = Organization.objects.create(name="organization")
        cls.vendor = Vendor.objects.create(org=org, name="vendor", is_offshore=True)

    @data(
        ["Osama Abdelmongy Abdalla", "BAKR", None, 1],
        ["Zayn al-Abidin Muhammad", "HUSAYN", None, 1],
        ["Husayn", "TAJIDEEN", None, 1],
        ["Adham Husayn", "TABAJA", None, 2],
        ["Husayn Ali", "FA'UR", None, 1],
        ["Jamal Husayn", "ZAYNIYAH", None, 1],
        ["Muhammad", "HUSAYN", None, 2],
        ["no name", "no name", None, 0],
        ["first_name", "last_name", None, 0],
        ["first", "last", "Emerson No. 148 Piso 7", 1],
        ["first", "last", "Ibex House, The Minories", 1],
        ["first", "last", "Grantley Adams Airport, Christ Church", 1],
        ["first", "last", "Toribio Ortega No. 6072-1 Colonia Fco. Villa", 1],
        ["first", "last", "PO Box 15875/7177, 144 Mirdamad Blvd", 1],
        ["first", "last", "Chinar Road, University Town", 1],
        ["first", "last", "Helene Meyer Ring 10-1415-80809", 1],
        ["first", "last", "no address found", 0],
        ["first", "last", "new address", 0],
    )
    @unpack
    def test_contact_search(self, first: str, last: str, address: str, expected_results: int):
        contact = Contact(
            vendor=self.vendor,
            first_name=first,
            last_name=last,
            line_1=address,
            role=ContactRole.ACCOUNTING,
        )
        contact.save()
        res = contact_search(contact=contact)
        self.assertEqual(len(res), expected_results)

    def test_273_incorrect_match_results(self):
        contact = Contact.objects.create(vendor=self.vendor, first_name="Abdelrahman", last_name="NUREY")
        results = contact_search(contact)
        self.assertEqual(len(results), 1)  # one result

        result = results[0]
        self.assertEqual(result.total_sdn, 1)  # 1 sdn
        self.assertEqual(result.total_address, 1)  # 1 address
        self.assertEqual(result.total_alias, 5)  # 5 aliases

    def test_280_incorrect_alias_count(self):
        contact = Contact.objects.create(vendor=self.vendor, first_name="Jamil", last_name="Hamie")
        results = contact_search(contact)
        self.assertEqual(len(results), 1)  # one result

        result = results[0]
        self.assertEqual(result.total_sdn, 1)  # 1 sdn
        self.assertEqual(result.total_address, 1)  # 1 address
        self.assertEqual(result.total_alias, 29)  # 29 aliases

    def test_274_contact_address_search_returning_incorrect_results(self):
        contact = Contact.objects.create(
            vendor=self.vendor, line_1="46 Varshavskoye Highway", city="Moscow Russia", zip_code="115230"
        )
        results = contact_search(contact)
        self.assertEqual(len(results), 1)  # one result

        result = results[0]
        self.assertEqual(result.total_sdn, 1)  # 1 sdn
        self.assertEqual(result.total_address, 1)  # 1 address
        self.assertEqual(result.total_alias, 3)  # 3 aliases
