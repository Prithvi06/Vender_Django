from unittest.mock import patch

from ddt import data, ddt, unpack
from django.test import TestCase
from organizations.models import Organization

from apps.administrator.tasks import fetch_weekly_ofac_list
from apps.vendor.models import Vendor
from apps.vendor.tasks import vendor_search

from .tests import (
    _mock_download_ofac_address_file,
    _mock_download_ofac_alternate_file,
    _mock_download_ofac_sdn_file,
)


@ddt
class TestVendorSearch(TestCase):
    org: Organization

    @classmethod
    @patch("apps.administrator.tasks.download_ofac_sdn_file", _mock_download_ofac_sdn_file)
    @patch("apps.administrator.tasks.download_ofac_alternate_file", _mock_download_ofac_alternate_file)
    @patch("apps.administrator.tasks.download_ofac_address_file", _mock_download_ofac_address_file)
    def setUpTestData(cls):
        fetch_weekly_ofac_list()
        cls.org = Organization.objects.create(name="organization")

    @data(
        ["GALAX TRADING CO., LTD", 1],
        ["ANGLO-CARIBBEAN CO., LTD.", 1],
        ["NORDSTRAND LTD.", 1],
        ["PRENSA LATINA CANADA LTD.", 1],
        ["M & S SYNDICATE (PVT) LTD.", 1],
        ["ZIMBABWE DEFENCE INDUSTRIES (PVT) LTD.", 1],
        ["ARCHI CENTRE I.C.E. LIMITED", 1],
        ["ADVANCED ELECTRONICS DEVELOPMENT, LTD", 1],
        ["bad vendor", 0],
        ["Not Matched", 0],
    )
    @unpack
    def test_vendor_search_by_name(self, name: str, expected_results: int):
        vendor = Vendor.objects.create(org=self.org, name=name, is_offshore=True)
        res = vendor_search(vendor=vendor)
        self.assertEqual(len(res), expected_results)

    def test_275_galax_trading_co_company_name(self):
        vendor = Vendor.objects.create(org=self.org, name="GALAX TRADING CO", is_offshore=True)
        results = vendor_search(vendor)
        self.assertEqual(len(results), 1)  # one result

        result = results[0]
        self.assertEqual(result.total_sdn, 1)
        self.assertEqual(result.total_address, 1)
        self.assertEqual(result.total_alias, 1)
