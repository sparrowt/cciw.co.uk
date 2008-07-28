# some models for use in tagging
from cciw.cciwmain.models import Member, Post, Topic
# the Tag model
from cciw.tagging.models import Tag
from cciw.tagging.utils import get_content_type_id, get_pk_as_str
from django.test import TestCase

class TestTagBase(TestCase):
    fixtures = ['basic.yaml', 'basic_topic.yaml', 'test_members.yaml']

    def tearDown(self):
        Tag.objects.all().delete()

    @staticmethod
    def _get_member():
        return Member.objects.get(user_name='test_member_1')

    @staticmethod
    def _get_post():
        return Post.objects.get(pk=1)

    @staticmethod
    def _get_topic():
        return Topic.objects.get(pk=1)

class TestTag(TestTagBase):

    def test_create(self):
        """
        Test basic creation, implicitly testing GenericForeignKey
        and related utility functions.
        """
        m = self._get_member()
        p = self._get_member()
        t = Tag(text='test')
        t.target = p
        t.creator = m
        t.save()

        t = Tag.objects.get(text='test')
        self.assertEqual(t.target, p)
        self.assertEqual(get_pk_as_str(p), t.target_id)
        self.assertEqual(get_content_type_id(p), t.target_ct_id)

        self.assertEqual(t.creator, m)
        self.assertEqual(get_pk_as_str(m), t.creator_id)
        self.assertEqual(get_content_type_id(m), t.creator_ct_id)

    def test_delete_target(self):
        """
        Ensure that tags are deleted when their targets are
        """
        m = self._get_member()
        p = self._get_post()
        t = Tag(text='test')
        t.target = p
        t.creator = m
        t.save()

        p_id = get_pk_as_str(p) # p.delete will set p.id = None
        self.assertEqual(Tag.objects.filter(target_id=p_id).count(), 1)
        p.delete()
        self.assertEqual(Tag.objects.filter(target_id=p_id).count(), 0)

    def test_delete_creator(self):
        """
        Ensure that tags are deleted when their creators are
        """
        m = Member.objects.get(user_name='test_member_1')
        p = Post.objects.get(pk=1)
        t = Tag(text='test')
        t.target = p
        t.creator = m
        t.save()

        m_id = get_pk_as_str(m) # m.delete will set m.id = None
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 1)        
        m.delete()
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 0)

class TestGetTargets(TestTagBase):
    """
    Tests for the Tag.get_targets method.
    """
    fixtures = ['basic.yaml', 'basic_topic.yaml', 'test_members.yaml']

    def tearDown(self):
        Tag.objects.all().delete()    

    def test_get_text(self):
        """
        Tests simply asking for a 'text' value
        """
        m = self._get_member()
        p = self._get_post()
        tp = self._get_topic()
        t1 = Tag(text='test')
        t1.target = p
        t1.creator = m
        t1.save()

        t2 = Tag(text='another')
        t2.target = p
        t2.creator = m
        t2.save()
        
        t3 = Tag(text='test')
        t3.target = tp
        t3.creator = m
        t3.save()
        
        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test')],
                         [('test', tp, 1), ('test', p, 1)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('another')],
                         [('another', p, 1)])
