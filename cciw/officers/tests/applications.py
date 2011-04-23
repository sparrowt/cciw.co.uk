import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.tests.references import OFFICER_USERNAME, OFFICER_PASSWORD

class ApplicationModel(TestCase):
    fixtures = ['basic.json', 'officers_users.json', 'references.json']

    def test_referees_get(self):
        """Tests the Application.referees getter utility"""
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        self.assertEqual(app.referees[0].name, app.referee1_name)
        self.assertEqual(app.referees[1].name, app.referee2_name)
        self.assertEqual(app.referees[0].address, app.referee1_address)
        self.assertEqual(app.referees[0].tel, app.referee1_tel)
        self.assertEqual(app.referees[0].mobile, app.referee1_mobile)
        self.assertEqual(app.referees[0].email, app.referee1_email)

    def test_referees_get_badattr(self):
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        self.assertRaises(AttributeError, lambda: app.references[0].badattr)

    def test_referees_set(self):
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        app.referees[0].name = "A new name"
        self.assertEqual(app.referee1_name, "A new name")

    def test_referees_set_extra_attrs(self):
        """Tests that we can set and retrieve additional attributes,
        not just ones defined as part of Application model"""

        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        app.referees[0].some_extra_attr = "Hello"
        self.assertEqual(app.referees[0].some_extra_attr, "Hello")

    def test_references(self):
        for appid in [1,2,3]:
            app = Application.objects.get(id=appid)
            self.assertEqual(app.references[0], app.reference_set.get(referee_number=1))
            self.assertEqual(app.references[1], app.reference_set.get(referee_number=2))


class PersonalApplicationList(TestCase):

    fixtures = ['basic.json', 'officers_users.json']

    _create_button = """<input type="submit" name="new" value="Create" """
    _edit_button = """<input type="submit" name="edit" value="Edit" """

    def setUp(self):
        self.client.login(username=OFFICER_USERNAME, password=OFFICER_PASSWORD)
        self.url = reverse('cciw.officers.views.applications')
        self.user = User.objects.get(username=OFFICER_USERNAME)
        self.user.application_set.all().delete()
        # Set Camps so that one is in the future, and one in the past,
        # so that is possible to have an application for an old camp
        Camp.objects.filter(id=1).update(start_date=datetime.date.today() + datetime.timedelta(100-365),
                                         end_date=datetime.date.today() + datetime.timedelta(107-365))
        Camp.objects.filter(id=2).update(start_date=datetime.date.today() + datetime.timedelta(100),
                                         end_date=datetime.date.today() + datetime.timedelta(107))


    def test_get(self):
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)
        self.assertContains(resp, "Your applications")

    def test_no_existing_application(self):
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)
        self.assertNotContains(resp, self._edit_button)

    def test_finished_application(self):
        app = self.user.application_set.create(finished=True,
                                               date_submitted=datetime.date.today())
        resp = self.client.get(self.url)
        self.assertContains(resp, self._create_button)

    def test_finished_application(self):
        app = self.user.application_set.create(finished=True,
                                               date_submitted=datetime.date.today()
                                               - datetime.timedelta(365))
        resp = self.client.get(self.url)
        self.assertContains(resp, self._create_button)

    def test_finished_application_recent(self):
        app = self.user.application_set.create(finished=True,
                                               date_submitted=datetime.date.today())
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)

    def test_unfinished_application(self):
        app = self.user.application_set.create(finished=False,
                                               date_submitted=datetime.date.today())
        resp = self.client.get(self.url)
        self.assertContains(resp, self._edit_button)

    def test_create(self):
        app = self.user.application_set.create(finished=True,
                                               date_submitted=datetime.date.today() - datetime.timedelta(365))
        resp = self.client.post(self.url, {'new':'Create'})
        self.assertEqual(302, resp.status_code)
        self.assertEqual(len(self.user.application_set.all()), 2)

    def test_create_when_already_done(self):
        # Should not create a new application if a recent one is submitted
        app = self.user.application_set.create(finished=True,
                                               date_submitted=datetime.date.today())
        resp = self.client.post(self.url, {'new':'Create'})
        self.assertEqual(200, resp.status_code)
        self.assertEqual(list(self.user.application_set.all()), [app])
