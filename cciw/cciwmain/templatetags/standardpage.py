from django.utils.http import urlquote, urlencode
from django import template
from cciw.cciwmain.models import HtmlChunk, Member, Post, Topic, Photo
from cciw.cciwmain.common import standard_subs
from cciw.cciwmain.utils import get_member_link, obfuscate_email, get_member_icon, get_current_domain
from cciw.middleware.threadlocals import get_current_member
from django.utils.html import escape
from django.conf import settings
from cciw.tagging import utils as tagging_utils
from cciw.tagging.models import Tag

class EmailNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        return obfuscate_email(self.nodelist.render(context))

def do_email(parser, token):
    """
    Obfuscates the email address between the
    'email' and 'endemail' tags.
    """
    nodelist = parser.parse(('endemail',))
    parser.delete_first_token()
    return EmailNode(nodelist)

class MemberLinkNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        user_name = self.nodelist.render(context)
        return get_member_link(user_name)

def do_member_link(parser, token):
    """
    Creates a link to a member, using the member name between the
    'memberlink' and 'endmemberlink' tags.
    """
    nodelist = parser.parse(('endmemberlink',))
    parser.delete_first_token()
    return MemberLinkNode(nodelist)

class MemberIconNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        user_name = self.nodelist.render(context)
        return get_member_icon(user_name)

def do_member_icon(parser, token):
    """
    Creates an <img> tag for a member icon, using the member name between the
    'membericon' and 'endmembericon' tags.
    """
    nodelist = parser.parse(('endmembericon',))
    parser.delete_first_token()
    return MemberIconNode(nodelist)

class RenderHtmlChunk(template.Node):
    def __init__(self, chunk_name):
        self.chunk_name = chunk_name

    def render(self, context):
        chunk = getattr(self, 'chunk', None)
        if chunk is None:
            chunk = HtmlChunk.objects.get(name=self.chunk_name)
            self.chunk = chunk
        return chunk.render(context['request'])

def do_htmlchunk(parser, token):
    """
    Renders an HtmlChunk. It takes a single argument,
    the name of the HtmlChunk to find.
    """
    bits = token.contents.split(" ", 1)
    return RenderHtmlChunk(bits[1])

class AtomFeedLink(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            return u'<link rel="alternate" type="application/atom+xml" href="%(url)s?format=atom" title="%(title)s" />' \
            % {'url': context['request'].path, 'title': title }
        else:
            return u''

class AtomFeedLinkVisible(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            thisurl = context['request'].path
            thisfullurl = 'http://%s%s' % (get_current_domain(), thisurl)
            return (u'<a class="atomlink" href="%(atomurl)s" rel="external" title="%(atomtitle)s" >' +
                    u' <img src="%(atomimgurl)s" alt="Feed icon" /></a> ' +
                    u' <a href="/website/feeds/" title="Help on Atom feeds">?</a> |' +
                    u' <a class="atomlink" href="%(emailurl)s" rel="external" title="Subscribe to this page by email">' +
                    u' <img src="%(emailimgurl)s" alt="Email icon" /></a> ' +
                    u' <a href="/website/feeds/#emailupdates" title="Help on Email updates">?</a> |') \
            % dict(atomurl="%s?format=atom" % thisurl,
                   atomtitle=title,
                   atomimgurl="%s/images/feed.gif" % settings.MEDIA_URL,
                   emailurl=escape("http://www.rssfwd.com/rssfwd/preview?%s" % urlencode({'url':thisfullurl, 'submit url':'Submit'})),
                   emailimgurl="%s/images/email.gif" % settings.MEDIA_URL
               )
        else:
            return ''

class TagSummaryList(template.Node):
    def __init__(self, target_var_name):
        self.target_var_name = target_var_name

    def render(self, context):
        target = template.resolve_variable(self.target_var_name, context)
        tagsummaries = Tag.objects.get_tag_summaries(target=target, order='count')
        model_name = target.__class__.__name__.lower()
        model_id = tagging_utils.get_pk_as_str(target)
        output = []
        for tagsum in tagsummaries:
            output.append(u'<a class="smtag smweight%s" title="View other items with this tag" href="/tags/%s/">%s</a>' % \
                            (tagsum.weight(), tagsum.text, tagsum.text))
            output.append(u'<a class="tagcount" title="See details of this tag" href="/tag_targets/%s/%s/%s/">x%s</a> ' % \
                            (model_name, model_id, tagsum.text, tagsum.count))
        return ''.join(output)

def do_tag_summary_list(parser, token):
    """
    Renders a list of tag summaries for an object, with links to
    full details.

    Example::

        {% tag_summary_list for post %}
    """
    tokens = token.contents.split()
    if not len(tokens) == 3:
        raise template.TemplateSyntaxError, "%r tag requires 2 arguments" % tokens[0]
    if tokens[1] != 'for':
        raise template.TemplateSyntaxError, "First argument in %r tag must be 'for'" % tokens[0]

    return TagSummaryList(tokens[2])


class AddTagLink(template.Node):
    def __init__(self, target_var_name):
        self.target_var_name = target_var_name

    def render(self, context):
        target = template.resolve_variable(self.target_var_name, context)
        request = context['request'] # requires request to be in the context
        model_name = target.__class__.__name__.lower()
        model_id = tagging_utils.get_pk_as_str(target)

        return u'<a class="addtag" href="/edit_tag/%s/%s/?r=%s" title="Add/edit tags for this %s">+</a>' % \
                (model_name, model_id, escape(urlquote(request.get_full_path())), model_name)

def do_add_tag_link(parser, token):
    """
    Renders a link for adding a tag to an object

    Syntax::

        {% add_tag_link for [object] %}

    Example usage::

        {% add_tag_link for post %}
    """
    tokens = token.contents.split()
    if not len(tokens) == 3:
        raise template.TemplateSyntaxError, "%r tag requires 2 arguments" % tokens[0]
    if tokens[1] != 'for':
        raise template.TemplateSyntaxError, "First argument in %r tag must be 'for'" % tokens[0]

    return AddTagLink(tokens[2])

register = template.Library()
register.filter(standard_subs)
register.filter(obfuscate_email)
register.tag('email', do_email)
register.tag('memberlink', do_member_link)
register.tag('membericon', do_member_icon)
register.tag('htmlchunk', do_htmlchunk)
register.tag('atomfeedlink', AtomFeedLink)
register.tag('atomfeedlinkvisible', AtomFeedLinkVisible)
register.tag('add_tag_link', do_add_tag_link)
register.tag('tag_summary_list', do_tag_summary_list)
