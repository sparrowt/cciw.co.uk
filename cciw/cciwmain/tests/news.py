from __future__ import with_statement
from client import CciwClient
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.file import SessionStore
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from cciw.cciwmain.models import Topic, Member, NewsItem, Post, Forum
from cciw.cciwmain.tests.members import TEST_MEMBER_USERNAME
from cciw.cciwmain.tests.utils import init_query_caches, FuzzyInt
from cciw.cciwmain.views import forums


class NewsPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'news.json']

    def setUp(self):
        self.client = CciwClient()


    # Short news items contain BBCode
    def test_shortews_html(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertTrue("Bits &amp; Pieces" in response.content,
                        "Subject not present or not escaped properly")

        self.assertTrue("Summary <b>with bbcode</b>" in response.content,
                        "BBCode content not present or not escaped properly")

    def test_shortnews_atom(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)

        self.assertTrue("Bits &amp; Pieces" in response.content,
                        "Subject not present or not escaped properly")

        self.assertTrue("Summary &lt;b&gt;with bbcode&lt;/b&gt;" in response.content,
                        "BBCode content not present or not escaped properly")


    # `Long' news items contain HTML
    def test_longnews_html(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertTrue("Fish &amp; Chips" in response.content,
                        "Subject not present or not escaped properly")

        self.assertTrue("<p>Full item with <i>html" in response.content,
                        "HTML content not present or not escaped properly")


    def test_longnews_atom(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)

        self.assertTrue("Fish &amp; Chips" in response.content,
                        "Subject not present or not escaped properly")

        self.assertTrue("&lt;p&gt;Full item with &lt;i&gt;html" in response.content,
                        "HTML content not present or not escaped properly")


class AllNewsPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'news.json']

    def test_query_count(self):
        """
        Test the number of queries (HTML and Atom)
        """
        path = reverse('cciwmain.site-news-index')
        member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        forum = Forum.objects.get(location='news/')
        factory = RequestFactory()
        init_query_caches()

        # Make sure we have lots of news items
        num = 100
        assert num > settings.FORUM_PAGINATE_TOPICS_BY
        for i in xrange(num):
            news_item = NewsItem.create_item(member, "Subject %s" % i,
                                             "Short item %s" % i)
            topic = Topic.create_topic(member, "Topic %s" % i, forum)
            topic.news_item = news_item
            topic.save()
            post = Post.create_post(member, "Message %s" % i, topic, None)

        request = factory.get(path)
        request.session = SessionStore()
        request.user = AnonymousUser()
        with self.assertNumQueries(6):
            resp = forums.news(request)
            resp.render()
            expected_count = settings.FORUM_PAGINATE_NEWS_BY
            self.assertContains(resp, "<a title=\"Information about",
                                count=FuzzyInt(expected_count, expected_count + 2))

        request = factory.get(path, {'format':'atom'})
        request.session = SessionStore()
        request.user = AnonymousUser()
        with self.assertNumQueries(2):
            response = forums.news(request)
            resp.render()
            self.assertEqual(response['Content-Type'], 'application/atom+xml')
