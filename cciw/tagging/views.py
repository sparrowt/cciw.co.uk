from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views.generic import list_detail
from cciw.tagging import utils as tagging_utils
from cciw.tagging.models import Tag

# For Python 2.3
if not hasattr(__builtins__, 'set'):
    from sets import Set as set

POPULAR_TAGS_LIMIT = 20

def _get_base_attrs_for_objs(creator, target):
    retval = {}
    if creator:
        retval['creator_id'] = creator._get_pk_val()
        retval['creator_ct_id'] = tagging_utils.get_content_type_id(creator.__class__)
    if target:
        retval['target_id'] = target._get_pk_val()
        retval['target_ct_id'] = tagging_utils.get_content_type_id(target.__class__)
    return retval

def _get_search_attrs(base_attrs):
    """Turns 'base attributes' dictionary into a dict
    that can be passed to QuerySet.filter()"""
    return dict([(k.replace('_ct_id', '_ct__id__exact'), v) 
                    for k, v in base_attrs.iteritems()])

def recent_popular(request, creator=None, target=None, creator_model=None, target_model=None,
        extra_context=None, popular_tags_limit=POPULAR_TAGS_LIMIT, 
        popular_tags_order='text', text=None, extra_handler=None, **kwargs):
    """View that displays a list of recent tags, with paging,
    and a list of popular tags.  Both lists are filtered by the 'creator', 
    'target', 'creator_model' and 'target_model' parameters if given.
    
    The recent tags are displayed using the list_detail.object_list generic view,
    and the full objects are displayed.  The popular tags are available in the
    context as a list of TagSummary objects, with the name 'popular_tags'.
    
    'popular_tags_order' is the ordering to apply to the popular tags. It can 
    be 'count' (descending popularity) or 'text'.(alphabetical, ascending).
    
    'text' limits the search to tags with a specific 'text' value. (not generally useful)
    
    The template context variables are the list_detail.object_list ones, 
    plus 'popular_tags' (a list of TagSummary objects), plus 'text', 'target'
    and 'creator'.
    
    extra_handler is an optional callable that can be used to generate an alternative
    rendering for the queryset (e.g. an Atom feed).  If provided, it should be a callable
    that takes the request and the Tag queryset as it only parameters, and returns
    None if decides not to handle the request, or an object (e.g. HttpResponse)
    to be returned otherwise.
    
    kwargs can be used to pass additional parameters to list_detail.object_list
    generic view (e.g. template_name, paginate_by etc).
    """

    base_attrs = _get_base_attrs_for_objs(creator, target)
    if text is not None:
        base_attrs['text'] = text
    if target_model is not None:
        base_attrs['target_ct_id'] = tagging_utils.get_content_type_id(target_model)
    if creator_model is not None:
        base_attrs['creator_ct_id'] = tagging_utils.get_content_type_id(creator_model)

    queryset = Tag.objects.filter(**_get_search_attrs(base_attrs))
    if extra_handler is not None:
        resp = extra_handler(request, queryset)
        if resp is not None: return resp

    popular_tags = Tag.objects.get_tag_summaries(target=target, creator=creator,
        target_model=target_model, creator_model=creator_model, limit=popular_tags_limit,
        order=popular_tags_order, text=text)
    if extra_context is None:
        extra_context = {}
    extra_context.update(base_attrs)
    extra_context['target'] = target
    extra_context['creator'] = creator
    extra_context['popular_tags'] = popular_tags

    return list_detail.object_list(request, queryset, allow_empty=True, 
                extra_context=extra_context, **kwargs)

class TagTargetPseudoQuery(object):
    """Pseudo-QuerySet used for passing into generic view."""
    def __init__(self, text, target_model):
        self.text = text
        self.target_model = target_model
        

    def _clone(self):
        return self # we don't need the generic view to clone us

    def count(self):
        return Tag.objects.get_target_count(self.text, self.target_model)
    
    def __getitem__(self, k):
        "Retrieve an item or slice from the set of results."
        assert isinstance(k, slice) # we don't need to handle anything else
        offset = k.start
        if k.stop is not None and k.start is not None:
            limit = k.stop - k.start
        else:
            limit = k.stop
        return Tag.objects.get_targets(self.text, limit=limit, 
            offset=offset, target_model=self.target_model)

def targets_for_text(request, text, target_model=None, template_name=None,
            extra_context=None, **kwargs):
        """Displays a list of objects 'TagTarget' objects Tagged with the given
        'text' value, ordered by decreasing popularity, with paging. 
        To search for objects with several different 'text' values, 
        pass 'text' as a space separated list.
        
        Additional kwargs are passed into list_detail.object_list generic view.
        
        Context variables are the list_detail.object_list ones, plus
        'text' (the value passed in), textlist (a list of text values,
        i.e. 'text' split on spaces), plus target_ct (the ContentType
        object for the target_model passed in).
        """
        assert template_name is not None, "template_name is required"
        queryset = TagTargetPseudoQuery(text, target_model)
        if extra_context is None:
            extra_context = {}
        extra_context['text'] = text
        if target_model is not None:
            extra_context['target_ct'] = tagging_utils.get_content_type_id(target_model)
        return list_detail.object_list(request, queryset, allow_empty=True,
            template_name=template_name, extra_context=extra_context, **kwargs)


def create_update(request, creator=None, target=None, redirect_url=None,
        extra_context={}, template_name='tagging/create.html'):
    """View that creates or updates a set of tags for an object.
    
    The template context variables are the list_detail.object_list ones, 
    plus 'text' (a space separated list of current text values), and
    'target'.
    """
    
    if creator is None or target is None:
        raise Http404()

    base_attrs = _get_base_attrs_for_objs(creator, target)
    search_attrs = _get_search_attrs(base_attrs)

    tags = Tag.objects.filter(**search_attrs)

    currenttagset = set([tag.text for tag in tags])
    
    if request.POST.get('save'):
        # remove some possibly troublesome chars:
        text = tagging_utils.strip_unsafe_chars(request.POST.get('text', ''))
        newtagset = set(text.split())
        # Delete ones that have been removed
        for tagname in currenttagset - newtagset:
            Tag.objects.filter(**search_attrs).filter(text=tagname).delete()
        # Add new ones
        for tagname in newtagset - currenttagset:
            t = Tag(**base_attrs)
            t.text = tagname
            t.save()
        if redirect_url is None:
            redirect_url = request.POST.get('redirect_url', None)
        if redirect_url is None:
            redirect_url = request.GET.get('redirect_url', None)
        if redirect_url is not None:
            return HttpResponseRedirect(redirect_url)
            
        # Get the new set
        tags = Tag.objects.filter(**search_attrs)
        currenttagset = set([tag.text for tag in tags])
    
    # context dict
    c = {}
    c.update(base_attrs)
    c['target'] = tagging_utils.get_object(base_attrs['target_id'], base_attrs['target_ct_id'])
    c['creator'] = tagging_utils.get_object(base_attrs['creator_id'], base_attrs['creator_ct_id'])
    c['textlist'] = list(currenttagset)
    c['text'] = " ".join(currenttagset)
    if redirect_url:
        c['redirect_url'] = redirect_url
    ctx = RequestContext(request, c)
        
    return render_to_response(template_name, context_instance=ctx)
    
