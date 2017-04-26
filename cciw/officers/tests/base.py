from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django_dynamic_fixture import G

from cciw.accounts.models import BOOKING_SECRETARY_GROUP_NAME, DBS_OFFICER_GROUP_NAME, SECRETARY_GROUP_NAME
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.officers.models import Application, QualificationType, Reference

User = get_user_model()

OFFICER_USERNAME = 'joebloggs'
OFFICER_PASSWORD = 'test_normaluser_password'
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


def perm(codename, app_label, model):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    try:
        return Permission.objects.get(codename=codename, content_type=ct)
    except Permission.DoesNotExist:
        return G(Permission,
                 codename=codename,
                 content_type=ct)


class CreateQualificationTypesMixin(object):
    def create_qualification_types(self):
        self.first_aid_qualification, _ = QualificationType.objects.get_or_create(name="First Aid (1 day)")


class RequireQualificationTypesMixin(CreateQualificationTypesMixin):
    def setUp(self):
        super(RequireQualificationTypesMixin, self).setUp()
        self.create_qualification_types()


class SimpleOfficerSetupMixin(BasicSetupMixin):
    """
    Sets up a single officer with minimal permissions
    """
    def setUp(self):
        super(SimpleOfficerSetupMixin, self).setUp()
        self.officer_user = G(User,
                              username=OFFICER_USERNAME,
                              first_name="Joe",
                              last_name="Bloggs",
                              is_active=True,
                              is_superuser=False,
                              is_staff=True,
                              email="joebloggs@somewhere.com",
                              permissions=[])
        self.officer_user.set_password(OFFICER_PASSWORD)
        self.officer_user.save()


class OfficersSetupMixin(SimpleOfficerSetupMixin):
    """
    Sets up a suite of officers with correct permissions etc.
    """
    def setUp(self):
        super(OfficersSetupMixin, self).setUp()
        self.leader_user = G(User,
                             username=LEADER_USERNAME,
                             first_name="Dave",
                             last_name="Stott",
                             is_active=True,
                             is_superuser=False,
                             is_staff=True,
                             email=LEADER_EMAIL,
                             permissions=[])
        self.leader_user.set_password(LEADER_PASSWORD)
        self.leader_user.save()

        # Associate with Person object
        self.default_leader.users.add(self.leader_user)

        self.booking_secretary_group = G(Group,
                                         name=BOOKING_SECRETARY_GROUP_NAME,
                                         permissions=[
                                             perm("add_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("change_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("delete_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("add_bookingaccount",
                                                  "bookings",
                                                  "bookingaccount"),
                                             perm("change_bookingaccount",
                                                  "bookings",
                                                  "bookingaccount"),
                                             perm("add_manualpayment",
                                                  "bookings",
                                                  "manualpayment"),
                                             perm("change_manualpayment",
                                                  "bookings",
                                                  "manualpayment"),
                                             perm("delete_manualpayment",
                                                  "bookings",
                                                  "manualpayment"),
                                             perm("change_payment",  # so they can view payment inlines
                                                  "bookings",
                                                  "payment"),
                                             perm("add_price",
                                                  "bookings",
                                                  "price"),
                                             perm("change_price",
                                                  "bookings",
                                                  "price"),
                                             perm("delete_price",
                                                  "bookings",
                                                  "price"),
                                             perm("add_accounttransferpayment",
                                                  "bookings",
                                                  "accounttransferpayment"),
                                             perm("change_accounttransferpayment",
                                                  "bookings",
                                                  "accounttransferpayment"),
                                             perm("delete_accounttransferpayment",
                                                  "bookings",
                                                  "accounttransferpayment"),
                                             perm("add_refundpayment",
                                                  "bookings",
                                                  "refundpayment"),
                                             perm("change_refundpayment",
                                                  "bookings",
                                                  "refundpayment"),
                                             perm("delete_refundpayment",
                                                  "bookings",
                                                  "refundpayment"),
                                             perm("change_camp",
                                                  "cciwmain",
                                                  "camp"),
                                             perm("add_qualificationtype",
                                                  "officers",
                                                  "qualificationtype"),
                                             perm("change_qualificationtype",
                                                  "officers",
                                                  "qualificationtype"),
                                             perm("delete_qualificationtype",
                                                  "officers",
                                                  "qualificationtype"),
                                         ],
                                         )

        self.booking_secretary = G(User,
                                   username=BOOKING_SECRETARY_USERNAME,
                                   is_active=True,
                                   is_superuser=False,
                                   is_staff=True,
                                   groups=[self.booking_secretary_group])
        self.booking_secretary.set_password(BOOKING_SECRETARY_PASSWORD)
        self.booking_secretary.save()

        self.secretary_group = G(Group,
                                 name=SECRETARY_GROUP_NAME,
                                 permissions=[
                                     perm("change_application",
                                          "officers",
                                          "application"),
                                     perm("add_qualificationtype",
                                          "officers",
                                          "qualificationtype"),
                                     perm("change_qualificationtype",
                                          "officers",
                                          "qualificationtype"),
                                     perm("delete_qualificationtype",
                                          "officers",
                                          "qualificationtype"),
                                 ],
                                 )

        self.secretary = G(User,
                           username=SECRETARY_USERNAME,
                           is_active=True,
                           is_superuser=False,
                           is_staff=True,
                           groups=[self.secretary_group])
        self.secretary.set_password(SECRETARY_PASSWORD)
        self.secretary.save()

        self.dbs_officer_group = G(Group,
                                   name=DBS_OFFICER_GROUP_NAME,
                                   permissions=[
                                       perm("add_dbscheck",
                                            "officers",
                                            "dbscheck"),
                                       perm("change_dbscheck",
                                            "officers",
                                            "dbscheck"),
                                       perm("delete_dbscheck",
                                            "officers",
                                            "dbscheck"),
                                       perm("add_dbsactionlog",
                                            "officers",
                                            "dbsactionlog"),
                                       perm("change_dbsactionlog",
                                            "officers",
                                            "dbsactionlog"),
                                       perm("delete_dbsactionlog",
                                            "officers",
                                            "dbsactionlog"),
                                   ])

        self.dbs_officer = G(User,
                             username=DBSOFFICER_USERNAME,
                             email=DBSOFFICER_EMAIL,
                             is_active=True,
                             is_superuser=False,
                             is_staff=True,
                             groups=[self.dbs_officer_group])
        self.dbs_officer.set_password(DBSOFFICER_PASSWORD)
        self.dbs_officer.save()


class ExtraOfficersSetupMixin(OfficersSetupMixin):
    """
    Sets up a set of normal officers who are on camp lists,
    along with those created by OfficersSetupMixin
    """

    def setUp(self):
        super(ExtraOfficersSetupMixin, self).setUp()

        self.officer1 = self.officer_user
        self.officer2 = G(User,
                          username="petersmith",
                          first_name="Peter",
                          last_name="Smith",
                          is_active=True,
                          is_superuser=False,
                          is_staff=True,
                          last_login="2008-04-23T14:49:25Z",
                          password="sha1$1b3b9$a8a863f2f021582d972b6e50629c8f8588de7bba",
                          email="petersmith@somewhere.com",
                          date_joined="2008-03-21T16:48:46Z"
                          )

        self.officer3 = G(User,
                          username="fredjones",
                          first_name="Fred",
                          last_name="Jones",
                          is_active=True,
                          is_superuser=False,
                          is_staff=True,
                          last_login="2008-04-23T14:49:25Z",
                          email="fredjones@somewhere.com",
                          date_joined="2008-03-21T16:48:46Z"
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
            date_submitted=datetime(year, 3, 1),
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
        application = G(Application, **fields)
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
        self.application4.date_submitted += timedelta(days=365)
        self.application4.save()

        # Dupe referee info:
        for r in self.application1.referees:
            self.application4.referee_set.create(
                referee_number=r.referee_number,
                name=r.name,
                email=r.email)


class RequireApplicationsMixin(DefaultApplicationsMixin):
    def setUp(self):
        super(RequireApplicationsMixin, self).setUp()
        self.create_default_applications()


class ReferenceHelperMixin(object):

    def create_complete_reference(self, referee):
        return G(Reference,
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
        super(CurrentCampsMixin, self).setUp()
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
        super(ReferenceSetupMixin, self).setUp()
        self.reference1_1 = self.create_complete_reference(self.application1.referees[0])
        self.application1.referees[1].log_request_made(None, timezone.now())
        self.application2.referees[1].log_request_made(None, timezone.now())
