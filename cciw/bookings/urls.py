from django.conf.urls.defaults import patterns, url

urlpatterns = \
    patterns('cciw.bookings.views',
             (r'^$', 'index'),
             (r'^start/$', 'start'),
             (r'^email-sent/$', 'email_sent'),
             (r'^v/(?P<account_id>[0-9A-Za-z]+)-(?P<token>.+)/$', 'verify_email'),
             (r'^v/failed/$', 'verify_email_failed'),
             (r'^account/$', 'account_details'),
             (r'^loggedout/$', 'not_logged_in'),
             (r'^add-camper-details/$', 'add_place'),
             (r'^edit-camper-details/(?P<id>\d+)/$', 'edit_place'),
             (r'^places-json/$', 'places_json'),
             (r'^account-json/$', 'account_json'),
             (r'^all-account-json/$', 'all_account_json'),
             (r'^booking-problems-json/$', 'booking_problems_json'),
             (r'^place-availability-json/$', 'place_availability_json'),
             (r'^expected-amount-json/$', 'get_expected_amount_due'),
             (r'^checkout/$', 'list_bookings'),
             (r'^pay/$', 'pay'),
             (r'^pay/done/$', 'pay_done'),
             (r'^pay/cancelled/$', 'pay_cancelled'),
             (r'^overview/$', 'account_overview'),
             (r'^logout/$', 'logout'),
             )