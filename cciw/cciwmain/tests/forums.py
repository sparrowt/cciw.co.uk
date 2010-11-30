from __future__ import with_statement
from cciw.cciwmain.tests.client import CciwClient
from cciw.cciwmain.tests.members import TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD, TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.file import SessionStore
from django.test import TestCase
from django.test.client import RequestFactory
from cciw.cciwmain.models import Topic, Member, Poll, Forum, Post
from cciw.cciwmain.views import forums
from django.core.urlresolvers import reverse
from datetime import datetime
from cciw.cciwmain import decorators

FORUM_1_YEAR = 2000
FORUM_1_CAMP_NUMBER = 1
ADD_POLL_URL =  reverse("cciwmain.camps.add_poll",
                        kwargs=dict(year=FORUM_1_YEAR, number=FORUM_1_CAMP_NUMBER))


class ForumPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'basic_topic.json']

    def setUp(self):
        self.client = CciwClient()
        self.factory = RequestFactory()
        self.forum = Forum.objects.get(id=1)

    def test_get(self):
        response = self.client.get(self.forum.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jill &amp; Jane")

    def test_atom(self):
        response = self.client.get(self.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jill &amp; Jane")
        self.assertEqual(response['Content-Type'], 'application/atom+xml')

    def test_query_count(self):
        """
        Test the number of queries for topic index (HTML and Atom)
        """
        member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        # Make sure we have lots of topics
        for i in xrange(100):
            topic = Topic.create_topic(member, "Topic %s" % i, self.forum)
            topic.save()
            post = Post.create_post(member, "Message %s" % i, topic, None)
            post.save()

        request = self.factory.get(self.forum.get_absolute_url())
        request.session = SessionStore()
        with self.assertNumQueries(6):
            forums.topicindex(request, title="Title", forum=self.forum)

        request = self.factory.get(self.forum.get_absolute_url(), {'format':'atom'})
        request.session = SessionStore()
        with self.assertNumQueries(3):
            forums.topicindex(request, title="Title", forum=self.forum)


class TopicPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'basic_topic.json']

    def setUp(self):
        self.client = CciwClient()
        self.factory = RequestFactory()
        self.topic = Topic.objects.get(id=1)

    def path(self):
        return self.topic.get_absolute_url()

    def test_topic_html(self):
        response = self.client.get(self.path())
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<h2>&lt;Jill &amp; Jane&gt;</h2>" in response.content,
                        "Subject not escaped correctly")
        self.assertTrue("A <b>unique message</b> with some bbcode &amp; &lt;stuff&gt; to be escaped" in response.content,
                        "Posts not escaped correctly")
        self.assertTrue('<a href="/camps/">Forums and photos</a>' in response.content,
                        "Breadcrumb not escaped properly")

    def test_topic_atom(self):
        response = self.client.get(self.path(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<title>CCIW - Posts on topic "&lt;Jill &amp; Jane&gt;"</title>' in response.content,
                        "Title not escaped properly")
        self.assertTrue('A &lt;b&gt;unique message&lt;/b&gt; with some bbcode &amp;amp; &amp;lt;stuff&amp;gt; to be escaped' in response.content,
                        "Message posts not escaped properly")
        self.assertEqual(response['Content-Type'], 'application/atom+xml')

    def test_query_count(self):
        """
        Test the number of queries for topic page (HTML and Atom)
        """
        member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        # Make sure we have lots of posts
        for i in xrange(100):
            post = Post.create_post(member, "Message %s" % i, topic=self.topic)
            post.save()


        request = self.factory.get(self.topic.get_absolute_url())
        request.session = SessionStore()
        request.user = AnonymousUser()
        with self.assertNumQueries(9):
            forums.topic(request, title_start="Title", topicid=self.topic.id)

        request = self.factory.get(self.topic.get_absolute_url(), {'format':'atom'})
        request.session = SessionStore()
        request.user = AnonymousUser()
        with self.assertNumQueries(2):
            forums.topic(request, title_start="Title", topicid=self.topic.id)


class CreatePollPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'basic_topic.json']

    def setUp(self):
        self.client = CciwClient()

    def _poll_data_1(self):
        return dict(
            title="Poll title",
            intro_text="This is a poll",
            polloptions="Option 1\nOption 2\nOption 3\n\nOption 4",
            outro_text="Outro text",
            voting_starts_0="2007-12-26",
            voting_starts_1="00:00",
            voting_ends_0="2007-12-29",
            voting_ends_1="00:00",
            rules="0",
            rule_parameter="1",
            )

    def test_cant_create_poll_if_anonymous(self):
        response = self.client.get(ADD_POLL_URL)
        # response should be a login form
        self.assertTrue(decorators.LOGIN_FORM_KEY in response.content)

    def test_cant_create_poll_if_not_poll_creator(self):
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        response = self.client.get(ADD_POLL_URL)
        # we should a permission denied
        self.assertEqual(response.status_code, 403, "Should get permission denied if trying to create a poll w/o enough permissions")

    def test_create_poll(self):
        poll_data = self._poll_data_1()
        # Precondition:
        self.assertEqual(Poll.objects.filter(title=poll_data['title']).count(), 0, "Precondition for test not satisfied")

        self.client.member_login(TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD)
        response = self.client.get(ADD_POLL_URL)
        # we should be OK
        self.assertEqual(response.status_code, 200)

        # Now do a post to the same URL
        response2 = self.client.post(ADD_POLL_URL, data=self._poll_data_1())

        # We get a redirection to the new page:
        self.assertEqual(response2.status_code, 302, "Should be redirected upon successful creation of poll")

        # Ensure the poll got created
        try:
            p = Poll.objects.get(title=poll_data['title'])
        except Poll.ObjectDoesNotExist:
            self.fail("Poll not created.")

        self.assertEqual(p.intro_text, poll_data['intro_text'])
        self.assertEqual(p.poll_options.count(), 4, "Poll does not have right number of options created")

    def test_edit_poll(self):
        self.test_create_poll()
        self.client.logout()

        # Get the poll just created.
        p = Poll.objects.get(created_by=TEST_POLL_CREATOR_USERNAME)

        self.client.member_login(TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD)
        url = reverse("cciwmain.camps.edit_poll",
                      kwargs=dict(year=FORUM_1_YEAR,
                                  number=FORUM_1_CAMP_NUMBER,
                                  poll_id=p.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    def test_cant_edit_someone_elses_poll(self):
        self.test_create_poll()
        self.client.logout()

        # Get the poll just created.
        p = Poll.objects.get(created_by=TEST_POLL_CREATOR_USERNAME)

        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        url = reverse("cciwmain.camps.edit_poll",
                      kwargs=dict(year=FORUM_1_YEAR,
                                  number=FORUM_1_CAMP_NUMBER,
                                  poll_id=p.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
