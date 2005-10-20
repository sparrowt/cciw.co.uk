from django.conf.urls.defaults import *

urlpatterns = patterns('cciw.apps.cciw.views',
	(r'^login/$', 'members.login'),
	(r'^members/$', 'members.index'),
	(r'^members/(?P<userName>[A-Za-z0-9_]+)/$', 'members.detail'),
	(r'^thisyear/$', 'camps.thisyear'),
	(r'^camps/$', 'camps.index'),
	(r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', 'camps.detail'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/$', 'camps.forum'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/(?P<topicnumber>\d+)/$', 'camps.topic'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', 'camps.gallery'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', 'camps.photo'),
	(r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', 'camps.oldcampgallery'),
	(r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', 'camps.oldcampphoto'),
	(r'^news/$', 'forums.topicindex', 
		{'title': 'News', 
		'template_name': 
		'forums/newsindex', 
		'paginate_by' : 6,
		'default_order': ('-createdAt',)}), 
	(r'^news/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'News'}), # TODO - create different template ?
	(r'^website/forum/$', 'forums.topicindex', {'title': 'Website forum',
		'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
	(r'^website/forum/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'Website forum',
		'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
	(r'^sites/$', 'sites.index'),
	(r'^sites/(?P<name>.*)/$', 'sites.detail'),
	(r'^awards/', 'awards.index'),
	(r'', 'htmlchunk.find')
)
