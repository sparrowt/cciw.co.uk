from datetime import date, datetime, timedelta

from django.contrib.auth.models import Group
from django.utils import timezone

from cciw.accounts.models import (BOOKING_SECRETARY_GROUP_NAME, DBS_OFFICER_GROUP_NAME, REFERENCE_CONTACT_GROUP_NAME,
                                  SECRETARY_GROUP_NAME, setup_auth_groups, User)
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.officers.models import Application, QualificationType, Reference


OFFICER_USERNAME = 'joebloggs'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER_EMAIL = "joebloggs@somewhere.com"
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = 'davestott'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER_EMAIL = 'leader@somewhere.com'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


BOOKING_SECRETARY_USERNAME = 'bookingsec'
BOOKING_SECRETARY_PASSWORD = 'a_password'
BOOKING_SECRETARY = (BOOKING_SECRETARY_USERNAME, BOOKING_SECRETARY_PASSWORD)


SECRETARY_USERNAME = 'mrsecretary'
SECRETARY_PASSWORD = 'test_password'
SECRETARY = (SECRETARY_USERNAME, SECRETARY_PASSWORD)


DBSOFFICER_USERNAME = 'mrsdbsofficer'
DBSOFFICER_PASSWORD = 'my_password'
DBSOFFICER_EMAIL = 'dbsofficer@somewhere.com'
DBSOFFICER = (DBSOFFICER_USERNAME, DBSOFFICER_PASSWORD)


class CreateQualificationTypesMixin(object):
    def create_qualification_types(self):
        self.first_aid_qualification, _ = QualificationType.objects.get_or_create(name="First Aid (1 day)")


class RequireQualificationTypesMixin(CreateQualificationTypesMixin):
    def setUp(self):
        super().setUp()
        self.create_qualification_types()


class SimpleOfficerSetupMixin(BasicSetupMixin):
    """
    Sets up a single officer with minimal permissions
    """
    def setUp(self):
        super().setUp()
        self.officer_user = factories.make_officer(
            username=OFFICER_USERNAME,
            first_name="Joe",
            last_name="Bloggs",
            email=OFFICER_EMAIL,
            password=OFFICER_PASSWORD
        )


class OfficersSetupMixin(SimpleOfficerSetupMixin):
    """
    Sets up a suite of officers with correct permissions etc.
    """
    def setUp(self):
        super().setUp()
        setup_auth_groups()
        self.leader_user = factories.make_officer(
            username=LEADER_USERNAME,
            first_name="Dave",
            last_name="Stott",
            email=LEADER_EMAIL,
            password=LEADER_PASSWORD,
        )

        # Associate with Person object
        self.default_leader.users.add(self.leader_user)

        self.booking_secretary_group = Group.objects.get(name=BOOKING_SECRETARY_GROUP_NAME)
        self.booking_secretary = factories.make_officer(
            username=BOOKING_SECRETARY_USERNAME,
            groups=[self.booking_secretary_group],
            password=BOOKING_SECRETARY_PASSWORD,
        )

        self.secretary_group = Group.objects.get(name=SECRETARY_GROUP_NAME)
        self.secretary = factories.make_officer(
            username=SECRETARY_USERNAME,
            groups=[self.secretary_group],
            password=SECRETARY_PASSWORD,
        )

        self.dbs_officer_group = Group.objects.get(name=DBS_OFFICER_GROUP_NAME)
        self.dbs_officer = factories.make_officer(
            username=DBSOFFICER_USERNAME,
            email=DBSOFFICER_EMAIL,
            groups=[self.dbs_officer_group],
            password=DBSOFFICER_PASSWORD,
        )

        self.reference_contact_group = Group.objects.get(name=REFERENCE_CONTACT_GROUP_NAME)
        self.safeguarding_coordinator = factories.make_officer(
            username="safeguarder",
            first_name="Safe",
            last_name="Guarder",
            contact_phone_number="01234 567890",
            groups=[self.reference_contact_group],
        )


class ExtraOfficersSetupMixin(OfficersSetupMixin):
    """
    Sets up a set of normal officers who are on camp lists,
    along with those created by OfficersSetupMixin
    """

    def setUp(self):
        super().setUp()

        self.officer1 = self.officer_user
        self.officer2 = factories.make_officer(
            username="petersmith",
            first_name="Peter",
            last_name="Smith",
            email="petersmith@somewhere.com",
        )

        self.officer3 = factories.make_officer(
            username="fredjones",
            first_name="Fred",
            last_name="Jones",
            email="fredjones@somewhere.com",
        )

        self.default_camp_1.invitations.create(officer=self.officer1)
        self.default_camp_1.invitations.create(officer=self.officer2)
        self.default_camp_1.invitations.create(officer=self.officer3)


class CreateApplicationMixin(object):
    def create_application(self, officer, year,
                           overrides=None,
                           referee1_overrides=None,
                           referee2_overrides=None):
        fields = dict(
            officer=officer,
            address2_address="123 abc",
            address2_from="2003/08",
            address2_to="2004/06",
            address3_address="456 zxc",
            address3_from="1996/11",
            address3_to="2003/08",
            address_country="UK",
            address_county="Yorkshire",
            address_email="hey@boo.com",
            address_firstline="654 Stupid Way",
            address_mobile="",
            address_postcode="XY9 8WN",
            address_since="2004/06",
            address_tel="01048378569",
            address_town="Bradford",
            allegation_declaration=False,
            birth_date="1911-02-07",
            birth_place="Foobar",
            christian_experience="Became a Christian at age 0.2 years",
            concern_declaration=False,
            concern_details="",
            court_declaration=False,
            court_details="",
            dbs_check_consent=True,
            dbs_number="",
            crime_declaration=False,
            crime_details="",
            date_saved=datetime(year, 3, 1),
            employer1_from="2003/09",
            employer1_job="Pilot",
            employer1_leaving="",
            employer1_name="Employer 1",
            employer1_to="0000/00",
            employer2_from="1988/10",
            employer2_job="Manager",
            employer2_leaving="Just because",
            employer2_name="Employer 2",
            employer2_to="2003/06",
            finished=True,
            full_maiden_name="",
            full_name="Joe Winston Bloggs",
            illness_details="",
            relevant_illness=False,
            youth_experience="Lots",
            youth_work_declined=False,
            youth_work_declined_details="",
        )
        if overrides:
            fields.update(overrides)
        application = Application.objects.create(**fields)
        for referee_number, ref_overrides in zip([1, 2], [referee1_overrides, referee2_overrides]):
            referee_fields = dict(
                referee_number=referee_number,
                address="Referee {0} Address\r\nLine 2".format(referee_number),
                email="referee{0}@email.co.uk".format(referee_number),
                mobile="",
                name="Referee{0} Name".format(referee_number),
                tel="01222 666666",
            )
            if ref_overrides:
                referee_fields.update(ref_overrides)

            application.referee_set.create(**referee_fields)
        return application


class DefaultApplicationsMixin(CreateApplicationMixin, ExtraOfficersSetupMixin):

    def create_default_applications(self):
        # Data: Applications 1 to 3 are in year 2000, for camps in summer 2000
        # Application 4 is for 2001
        self.application1 = self.create_application(
            self.officer1, 2000,
            referee2_overrides=dict(
                address="1267a Somewhere Road\r\nThereyougo",
                name="Mr Referee2 Name",
            ))

        self.application2 = self.create_application(
            self.officer2, 2000,
            overrides=dict(
                full_name="Peter Smith",
            ),
            referee1_overrides=dict(
                address="Referee 3 Address\r\nLine 2",
                email="referee3@email.co.uk",
                name="Mr Referee3 Name",
            ),
            referee2_overrides=dict(
                address="Referee 4 adddress",
                email="referee4@email.co.uk",
                name="Mr Referee4 Name",
            ))

        self.application3 = self.create_application(
            self.officer3, 2000,
            overrides=dict(
                full_name="Fred Jones",
            ),
            referee1_overrides=dict(
                address="Referee 5 Address\r\nLine 2",
                email="referee5@email.co.uk",
                name="Mr Refere5 Name",
            ),
            referee2_overrides=dict(
                address="Referee 6 adddress",
                email="",
                name="Mr Referee6 Name",
                tel="01234 567890",
            ))

        # Application 4 is like 1 but a year later

        self.application4 = Application.objects.get(id=self.application1.id)
        self.application4.id = None  # force save as new
        self.application4.date_saved += timedelta(days=365)
        self.application4.save()

        # Dupe referee info:
        for r in self.application1.referees:
            self.application4.referee_set.create(
                referee_number=r.referee_number,
                name=r.name,
                email=r.email)


class RequireApplicationsMixin(DefaultApplicationsMixin):
    def setUp(self):
        super().setUp()
        self.create_default_applications()


class ReferenceHelperMixin(object):

    def create_complete_reference(self, referee):
        return Reference.objects.create(
            referee=referee,
            referee_name="Referee1 Name",
            how_long_known="A long time",
            capacity_known="Pastor",
            known_offences=False,
            capability_children="Wonderful",
            character="Almost sinless",
            concerns="Perhaps too good for camp",
            comments="",
            date_created=datetime(2000, 2, 20),
        )


class CurrentCampsMixin(BasicSetupMixin):
    def setUp(self):
        super().setUp()
        # Make sure second camp has end date in future, otherwise we won't be able to
        # save. Previous camp should be one year earlier i.e in the past
        self.default_camp_1.start_date = date.today() + timedelta(100 - 365)
        self.default_camp_1.end_date = date.today() + timedelta(107 - 365)
        self.default_camp_1.save()
        self.default_camp_2.start_date = date.today() + timedelta(100)
        self.default_camp_2.end_date = date.today() + timedelta(107)
        self.default_camp_2.save()


class ReferenceSetupMixin(ReferenceHelperMixin, set_thisyear(2000), RequireApplicationsMixin):

    def setUp(self):
        super().setUp()
        self.reference1_1 = self.create_complete_reference(self.application1.referees[0])
        self.application1.referees[1].log_request_made(None, timezone.now())
        self.application2.referees[1].log_request_made(None, timezone.now())


class Factories:
    def __init__(self):
        self._user_counter = 0

    def make_officer(
            self,
            username=None,
            first_name='Joe',
            last_name='Bloggs',
            is_active=True,
            is_superuser=False,
            is_staff=True,
            email=None,
            password=None,
            groups=None,
            contact_phone_number='',
    ):
        username = username or self._make_auto_username()
        email = email or self._make_auto_email(username)
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_superuser=is_superuser,
            is_staff=is_staff,
            email=email,
            contact_phone_number=contact_phone_number,
        )
        if password:
            user.set_password(password)
            user.save()
        if groups:
            user.groups.set(groups)
        return user

    def _make_auto_username(self):
        self._user_counter += 1
        return f'auto_user_{self._user_counter}'

    def _make_auto_email(self, username=None):
        username = username or self._make_auto_username()
        return f'{username}@example.com'


factories = Factories()
