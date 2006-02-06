from django import template
from django.shortcuts import render_to_response
from django.http import Http404
from django.template import RequestContext

from cciw.apps.cciw.common import *
from cciw.apps.cciw.models import HtmlChunk, MenuLink

def find(request):
    try:
        link = MenuLink.objects.get(url=request.path)
    except MenuLink.DoesNotExist:  
        raise Http404()
        
    try:
        chunk = link.htmlchunk_set.all()[0]
    except HtmlChunk.DoesNotExist:
        raise Http404()
    
    c = RequestContext(request, standard_extra_context(title = chunk.page_title))
    chunk.render(c, 'contentBody')
    return render_to_response('cciw/standard', c)
