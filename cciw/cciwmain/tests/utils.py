from datetime import datetime, time
from unittest import mock

from django.contrib.sites.models import Site

from cciw.cciwmain import common
from cciw.cciwmain.utils import ensure_timezone_aware


def init_query_caches():
    """
    Initialise any cached values that do DB queries.

    This is useful to improve isolation of tests that check the number of queries used.
    """
    common.get_thisyear()
    Site.objects.get_current()


class FuzzyInt(int):
    def __new__(cls, lowest, highest):
        obj = super().__new__(cls, highest)
        obj.lowest = lowest
        obj.highest = highest
        return obj

    def __eq__(self, other):
        return other >= self.lowest and other <= self.highest

    def __repr__(self):
        return f"[{self.lowest}, {self.highest}]"


def set_thisyear(year):
    """
    Return mixin that monkey patches get_thisyear in tests
    """
    # This relies on modules doing:
    #
    #   from cciw.cciwmain import common
    #   ...
    #   common.get_thisyear()
    #
    # rather than:
    #
    #   from cciw.cciwmain.common import get_thisyear

    class ThisYearMixin:
        def setUp(self):
            super().setUp()
            thisyear_patcher = mock.patch("cciw.cciwmain.common.get_thisyear")
            mocked = thisyear_patcher.start()
            mocked.return_value = year
            self.thisyear_patcher = thisyear_patcher

        def tearDown(self):
            self.thisyear_patcher.stop()
            super().tearDown()

    return ThisYearMixin


def make_datetime(year, month, day, hour=0, minute=0, second=0):
    return ensure_timezone_aware(datetime(year, month, day, hour, minute, second))


def date_to_datetime(date_value):
    if date_value is None:
        return None
    return ensure_timezone_aware(datetime.combine(date_value, time(0, 0, 0)))


class _NotPassedType:
    """
    Sentinel value used when 'None' would be allowed due to a nullable database field.
    """


NotPassed = _NotPassedType()
