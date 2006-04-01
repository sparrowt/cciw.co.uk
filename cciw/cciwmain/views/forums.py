import datetime
from django.views.generic import list_detail
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings
from cciw.cciwmain.models import Forum, Topic, Photo, Post, Member, VoteInfo
from cciw.cciwmain.common import create_breadcrumb, standard_extra_context, get_order_option
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain.decorators import login_redirect
from django.utils.html import escape
from cciw.cciwmain import utils
from cciw.cciwmain.templatetags import bbcode
from cciw.cciwmain.decorators import member_required
from datetime import datetime


# Utility functions for breadcrumbs
def topicindex_breadcrumb(forum):
    return ["Topics"]

def photoindex_breadcrumb(gallery):
    return ["Photos"]

def topic_breadcrumb(forum, topic):
    return ['<a href="' + forum.get_absolute_url() + '">Topics</a>']

def photo_breadcrumb(gallery, photo):
    prev_and_next = ''
    try:
        previous_photo = Photo.objects.filter(id__lt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('-id')[0]
        prev_and_next += '<a href="%s" title="Previous photo">&laquo;</a> ' % previous_photo.get_absolute_url() 
    except Photo.DoesNotExist:
        prev_and_next += '&laquo; '
        
    try:
        next_photo = Photo.objects.filter(id__gt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('id')[0]
        prev_and_next += '<a href="%s" title="Next photo">&raquo;</a> ' % next_photo.get_absolute_url()
    except Photo.DoesNotExist:
        prev_and_next += '&raquo; '
        
    return ['<a href="' + gallery.get_absolute_url() + '">Photos</a>', str(photo.id), prev_and_next]
    
# Called directly as a view for /news/ and /website/forum/, and used by other views
def topicindex(request, title=None, extra_context=None, forum=None,
    template_name='cciw/forums/topicindex', breadcrumb_extra=None, paginate_by=settings.FORUM_PAGINATE_TOPICS_BY, default_order=('-last_post_at',)):
    "Displays an index of topics in a forum"
    if extra_context is None:
        if title is None:
            raise Exception("No title provided for page")
        extra_context = standard_extra_context(title=title)
        
    if forum is None:
        try:
            forum = Forum.objects.get(location=request.path[1:])
        except Forum.DoesNotExist:
            raise Http404
    extra_context['forum'] = forum
    
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topicindex_breadcrumb(forum))

    # TODO - searching

    order_by = get_order_option(
        {'aca': ('created_at', 'id'),
        'dca': ('-created_at', '-id'),
        'apc': ('post_count',),
        'dpc': ('-post_count',),
        'alp': ('last_post_at',),
        'dlp': ('-last_post_at',),
        },
        request, default_order)

    extra_context['default_order'] = 'dlp' # corresponds = '-last_post_at'
    topics = Topic.visible_topics.filter(forum__id__exact= forum.id).order_by(*order_by)

    return list_detail.object_list(request, topics,
        extra_context=extra_context, template_name=template_name,
        paginate_by=paginate_by, allow_empty=True)


# Called directly as a view for /news/ and /website/forum/, and used by other views
@member_required
def add_topic(request, breadcrumb_extra=None):
    "Displays a page for adding a topic to a forum"

    location = request.path[1:-len('add/')] # strip 'add/' bit
    try:
        forum = Forum.objects.get(location=location)
    except Forum.DoesNotExist:
        raise Http404

    cur_member = get_current_member()
    context = RequestContext(request, standard_extra_context(title='Add topic'))
    
    if not forum.open:
        context['message'] = 'This forum is closed - new topics cannot be added.'
    else:
        context['forum'] = forum
        context['show_form'] = True
    
    errors = []
    # PROCESS POST
    if forum.open and request.POST.has_key('post') or request.POST.has_key('preview'):
        subject = request.POST.get('subject', '').strip()
        msg_text = request.POST.get('message', '').strip()
        
        if subject == '':
            errors.append('You must enter a subject')
            
        if msg_text == '':
            errors.append('You must enter a message.')
        
        # TODO: short news items, long news items. polls
        context['message_text'] = bbcode.correct(msg_text)
        context['subject_text'] = subject
        if not errors:
            if request.POST.has_key('post'):
                topic = Topic.create_topic(cur_member, subject, forum)
                topic.save()
                post = Post.create_post(cur_member, msg_text, topic, None)
                post.save()
                if topic.hidden:
                    context['message'] = 'The topic has been created, but is hidden for now'
                    context['show_form'] = False
                else:
                    return HttpResponseRedirect('../%s/' % topic.id)
            else:
                context['preview'] = bbcode.bb2xhtml(msg_text)
    
    context['errors'] = errors
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(forum, None))
    return render_to_response('cciw/forums/add_topic', context_instance=context)

# Used as part of a view function
def process_post(request, topic, photo, context):
    """Processes a posted message for a photo or a topic.
    One of 'photo' or 'topic' should be set.
    context is the context dictionary of the page, to which
    'errors' or 'message' might be added."""

    cur_member = get_current_member()
    if cur_member is None:
        # silently failing is OK, should never get here
        return  
      
    if not request.POST.has_key('post') and \
       not request.POST.has_key('preview'):
        return # they didn't try to post
      
    errors = []
    if (topic and not topic.open) or \
        (photo and not photo.open):
        # Only get here if the topic was closed 
        # while they were adding a message
        errors.append('This thread is closed, sorry.')
        # For this error, there is nothing more to say so return immediately
        context['errors'] = errors
        return None
    
    msg_text = request.POST.get('message', '').strip()
    if msg_text == '':
        errors.append('You must enter a message.')
    
    context['errors'] = errors
    
    # Preview
    if request.POST.has_key('preview'):
        context['message_text'] = bbcode.correct(msg_text)
        if not errors:
            context['preview'] = bbcode.bb2xhtml(msg_text)

    # Post
    if not errors and request.POST.has_key('post'):
        post = Post.create_post(cur_member, msg_text, topic, photo)
        post.save()
        return HttpResponseRedirect(post.get_forum_url())

def process_vote(request, topic, context):
    """Processes any votes posted on the topic.
    topic is the topic that might have a poll.
    context is the context dictionary of the page, to which
    voting_errors or voting_message might be added."""

    if topic.poll_id is None:
        # No poll
        return
    
    poll = topic.poll

    cur_member = get_current_member()
    if cur_member is None:
        # silently failing is OK, should never get here
        return

    try:
        polloption_id = int(request.POST['polloption'])
    except (ValueError, KeyError):
        return # they didn't try to vote, or invalid input
      
    errors = []
    if not poll.can_anyone_vote():
        # Only get here if the poll was closed 
        # while they were voting
        errors.append('This poll is closed for voting, sorry.')
        context['voting_errors'] = errors
        return
    
    if not poll.can_vote(cur_member):
        errors.append('You cannot vote on this poll.  Please check the voting rules.')
        context['voting_errors'] = errors
    
    if not polloption_id in (po.id for po in poll.poll_options.all()):
        errors.append('Invalid option chosen')
        context['voting_errors'] = errors
    
    if not errors:
        voteinfo = VoteInfo(poll_option_id=polloption_id,
                            member=cur_member,
                            date=datetime.now())
        voteinfo.save()
        context['voting_message'] = 'Vote registered, thank you.'

def topic(request, title_start=None, template_name='cciw/forums/topic', topicid=0,
        introtext=None, breadcrumb_extra=None):
    """Displays a topic"""
    if title_start is None:
        raise Exception("No title provided for page")

    cur_member = get_current_member()

    try:
        topic = Topic.visible_topics.get(id=int(topicid))
    except Topic.DoesNotExist:
        raise Http404
    
    ### GENERAL CONTEXT ###
    # Add additional title
    title = utils.get_extract(topic.subject, 40)
    if len(title_start) > 0:
        title = title_start + ": " + title
    extra_context = standard_extra_context(title=title)

    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(topic.forum, topic))

    if introtext:
        extra_context['introtext'] = introtext

    ### PROCESSING ###
    # Process any message that they added.
    resp = process_post(request, topic, None, extra_context)
    if resp is not None:
        return resp
    process_vote(request, topic, extra_context)

    ### Topic ###
    extra_context['topic'] = topic
    if not topic.news_item_id is None:
        extra_context['news_item'] = topic.news_item

    if topic.open:
        if get_current_member() is not None:
            extra_context['show_message_form'] = True
        else:
            extra_context['login_link'] = login_redirect(request.get_full_path() + '#messageform')

    ### Poll ###
    if topic.poll_id is not None:
        poll = topic.poll
        extra_context['poll'] = poll
        
        # TODO handle voting on polls
        if request.GET.get('showvotebox', None):
            extra_context['show_vote_box'] = True
        else:
            extra_context['show_poll_results'] = True
        
        extra_context['allow_voting_box'] = \
            (cur_member is None and poll.can_anyone_vote()) or \
            (cur_member is not None and poll.can_vote(cur_member))

    ### POSTS ###
    posts = Post.visible_posts.filter(topic__id__exact=topic.id)
    if request.user.has_perm('cciwmain.edit_post'):
        extra_context['moderator'] = True

    return list_detail.object_list(request, posts,
        extra_context=extra_context, template_name=template_name,
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY, allow_empty=True)

def photoindex(request, gallery, extra_context, breadcrumb_extra):
    "Displays an a gallery of photos"
    extra_context['gallery'] = gallery    
    extra_context['breadcrumb'] =   create_breadcrumb(breadcrumb_extra + photoindex_breadcrumb(gallery))

    order_by = get_order_option(
        {'aca': ('created_at','id'),
        'dca': ('-created_at','-id'),
        'apc': ('post_count',),
        'dpc': ('-post_count',),
        'alp': ('last_post_at',),
        'dlp': ('-last_post_at',)},
        request, ('created_at', 'id'))
    extra_context['default_order'] = 'aca'

    photos = Photo.visible_photos.filter(gallery__id__exact=gallery.id).order_by(*order_by)
    
    return list_detail.object_list(request, photos, 
        extra_context=extra_context, template_name='cciw/forums/photoindex',
        paginate_by=settings.FORUM_PAGINATE_PHOTOS_BY, allow_empty=True)

def photo(request, photo, extra_context, breadcrumb_extra):
    "Displays a photo"
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + photo_breadcrumb(photo.gallery, photo))
    extra_context['photo'] = photo
    
    if photo.open:
        if get_current_member() is not None:
            extra_context['show_message_form'] = True
        else:
            extra_context['login_link'] = login_redirect(request.get_full_path() + '#messageform')

    # Process any message that they added.
    process_post(request, None, photo, extra_context)

    ## POSTS
    if request.user.has_perm('cciwmain.edit_post'):
        extra_context['moderator'] = True
    posts = Post.visible_posts.filter(photo__id__exact=photo.id)

    return list_detail.object_list(request, posts,
        extra_context=extra_context, template_name='cciw/forums/photo',
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY, allow_empty=True)

def posts(request):
    context = standard_extra_context(title="Recent posts")
    posts = Post.visible_posts.exclude(posted_at__isnull=True).order_by('-posted_at')
    return list_detail.object_list(request, posts,
        extra_context=context, template_name='cciw/forums/posts',
        allow_empty=True, paginate_by=settings.FORUM_PAGINATE_POSTS_BY)

def post(request, id):
    try:
        post = Post.visible_posts.get(pk=id)
    except Post.DoesNotExist:
        raise Http404()
    return HttpResponseRedirect(post.get_forum_url())
