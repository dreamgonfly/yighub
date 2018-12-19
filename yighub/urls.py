from django.conf.urls import url
from . import views

app_name = 'yighub'
urlpatterns = [
    url(r'^home/$', views.home, name='home'),
    url(r'^home_for_members/$', views.home_member.as_view(), name='home_for_member'),

    url(r'^join/$', views.join, name='join'),
    url(r'^login/$', views.login, name='login'),
    url(r'^login_check/$', views.login_check, name='login_check'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^profile/$', views.edit_profile, name='edit_profile'),
    url(r'^first_login/$', views.edit_profile, {'first_login':True}, name='first_login'),


    url(r'^letter/list/$', views.letters),
    url(r'^letter/send/$', views.send),
    url(r'^letter/receive/(?P<letter_id>\d+)/$', views.receive),

    url(r'^memo/create/$', views.create_memo, name='create_memo'),
    url(r'^memo/(?P<memo_id>\d+)/delete/$', views.delete_memo, name='delete_memo'),
    url(r'^memo/(?P<page>\d+)/$', views.memo, name='memo'),

    url(r'^news/(?P<page>\d+)/$', views.all_news, name='all_news'),    

    url(r'^search/(?P<board_id>\d+)/(?P<keyword>.+)/(?P<page>\d+)$', views.search, name='search'),
    url(r'^search_albums/(?P<keyword>.+)/(?P<page>\d+)/$', views.search_albums, name='search_albums'),

    url(r'^taskforce/create/$', views.create_taskforce, name='create_taskforce'), # can make taskforce board 
    url(r'^taskforce/(?P<taskforce_id>\d+)/edit/$', views.edit_taskforce, name='edit_taskforce'),    
    url(r'^taskforce/archive/$', views.taskforce_archive, name='taskforce_archive'),

    url(r'^albums/page/(?P<page>\d+)/$', views.albums, name='albums'),
    url(r'^albums/(?P<album_id>\d+)/photos/$', views.photos, name='photos'),
    url(r'^albums/create/$', views.create_album, name='create_album'),
    url(r'^albums/(?P<album_id>\d+)/photos/create/$', views.create_photos, name='create_photos'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/edit/$', views.edit_photo, name='edit_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/delete/$', views.delete_photo, name='delete_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/recommend/$', views.recommend_photo, name='recommend_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/recommend/delete/$', views.delete_recommend_photo, name='delete_recommend_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/comment/$', views.comment_photo, name='comment_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/comment/(?P<comment_id>\d+)/delete/$', views.delete_comment_photo, name='delete_comment_photo'),    
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/comment/(?P<comment_id>\d+)/reply/$', views.reply_comment_photo, name='reply_comment_photo'),
    url(r'^albums/(?P<album_id>\d+)/photos/(?P<photo_id>\d+)/comment/(?P<comment_id>\d+)/recommend/$', views.recommend_comment_photo, name='recommed_comment_photo'),
    
    
    url(r'^(?P<board>\w+)/news/(?P<page>\d+)/$', views.news, name='news'), # newest entries in member boards. every links to boards should be with page ( even 1)
    url(r'^(?P<board>\w+)/(?P<board_id>\d+)/page/(?P<page>\d+)/$', views.listing, name='listing'), # every member board is with page.
    url(r'^(?P<board>\w+)/(?P<board_id>\d+)/entry/create/$', views.create, name='create_in_board'), # to create entry in specific member board. include 'entry' to specify that it is about entry. and compatible with non-specific creation of board entry. views.pleasegive t a name.
    url(r'^(?P<board>\w+)/entry/create/$', views.create, name='create'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/$', views.read, name='read'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/edit/$', views.edit, name='edit'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/delete/$', views.delete, name='delete'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/reply/$', views.reply, name='reply'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/recommend/$', views.recommend, name='recommend'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/recommend/delete/$', views.delete_recommend, name='delete_recommend'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/comment/$', views.comment, name='comment'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/comment/(?P<comment_id>\d+)/delete/$', views.delete_comment, name='delete_comment'),    
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/comment/(?P<comment_id>\d+)/reply/$', views.reply_comment, name='reply_comment'),
    url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/comment/(?P<comment_id>\d+)/recommend/$', views.recommend_comment, name='recommend_comment'),
    #url(r'^(?P<board>\w+)/entry/(?P<entry_id>\d+)/comment/(?P<comment_id>\d+)/recommend/delete/$', views.recommend_comment, name='recommend_comment')

    #도메인 이름 변경
    ##About YIG
    url(r'^AboutYIG/Introduction/$', views.Introduction.as_view(), name="Public_Introduction"),
    url(r'^AboutYIG/Vision/$', views.Vision.as_view(), name="Public_Vision"),
    url(r'^AboutYIG/Activity/$', views.Activity.as_view(), name="Public_Activity"),
    url(r'^AboutYIG/History/$', views.History.as_view(), name="Public_History"),
    url(r'^AboutYIG/Clipping/$', views.Introduction.as_view(), name="Public_Clipping"),

    ##Recruiting
    url(r'^Recruiting/$', views.Recruiting.as_view(), name="Public_Recruiting"),
    url(r'^Recruiting/Apply/$', views.Apply.as_view(), name="Public_Apply"),
    url(r'^Recruiting/Schedule/$', views.Schedule.as_view(), name="Public_Schedule"),
    url(r'^Recruiting/FAQ/$', views.FAQ.as_view(), name="Public_FAQ"),

    #MemberProfile
    url(r'^MemberProfile/(?P<page>\d+)/$', views.MemberProfile.as_view(), name="Public_Member_Profile"),

    #Fund (Fund, 디테일)
    url(r'^Fund/SIMA-Fund/(?P<page>\d+)/$', views.SIM_A.as_view(), name="Public_SIM_A"),
    url(r'^Fund/SIMA-Fund/detail/(?P<pk>\d+)/$', views.Fund_detail.as_view(), name="Public_SIM_A_detail"),
    url(r'^Fund/SIMJS-Fund/(?P<page>\d+)/$', views.SIM_JS.as_view(), name="Public_SIM_JS"),
    url(r'^Fund/SIMJS-Fund/detail/(?P<pk>\d+)/$', views.Fund_detail.as_view(), name="Public_SIM_JS_detail"),
    url(r'^Fund/GFund/(?P<page>\d+)/$', views.Gfund.as_view(), name="Public_Gfund"),
    url(r'^Fund/GFund/detail/(?P<pk>\d+)/$', views.Fund_detail.as_view(), name="Public_G_detail"),
    url(r'^Fund/SFund/(?P<page>\d+)/$', views.Sfund.as_view(), name="Public_Sfund"),
    url(r'^Fund/SFund/detail/(?P<pk>\d+)/$', views.Fund_detail.as_view(), name="Public_S_detail"),
    url(r'^Fund/YIG_Universe/(?P<page>\d+)/$', views.YIG_Universe.as_view(), name="Public_YIG_Universe"),
    url(r'^Fund/YIG_Universe/detail/(?P<pk>\d+)/$', views.Fund_detail.as_view(), name="Public_Universe_detail"),

    #Research
    url(r'^Research/(?P<page>\d+)/$', views.Research.as_view(), name="Public_Research"),

    #Cotact
    url(r'^Contact/$', views.Contact.as_view(), name="Public_Contact"),

    #Test 임시 URL(완성 후 즉각 삭제 요망)
    url(r'^TopBar/$', views.TopBar_for_Visitor.as_view(), name="TopBar_for_Visitor"),
    url(r'^SubTopBar/$', views.SubTopBar_for_Visitor.as_view(), name="SubTopBar"),
    url(r'^TopBarMember/$', views.Topbar_member.as_view(), name="TopBar_for_Member"),

    #Members_Boards
    url('members/Boards/news/(?P<pk>\d+)', views.BoardsNews.as_view(), name='member_Boards_News'),
    url('members/Boards/Column/(?P<pk>\d+)', views.Column.as_view(), name='member_Column'),
    url('members/Boards/Data/(?P<pk>\d+)', views.Data.as_view(), name='member_Data'),
    url('members/Boards/Portfolio/(?P<pk>\d+)', views.Portfolio.as_view(), name='member_Portfolio'),
    url('members/Boards/Analysis/(?P<pk>\d+)', views.Analysis.as_view(), name='member_Analysis'),
    url('members/Boards/Notice/(?P<pk>\d+)', views.Notice.as_view(), name='member_Notice'),
    url('members/Boards/Etc/(?P<pk>\d+)', views.Etc.as_view(), name='member_Etc'),

    #Taskforce
    url('members/Taskforce/News/(?P<pk>\d+)', views.TaskforceNews.as_view(), name='member_Taskforce_News'),
    url('members/Taskforce/(?P<board_id>\d+)/(?P<page>\d+)', views.Taskforce.as_view(), name='member_Taskforce'),
]