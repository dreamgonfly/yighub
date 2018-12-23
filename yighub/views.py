# -*- coding: utf-8 -*-

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, render, redirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.views.generic import TemplateView, DetailView
import mimetypes
import pdb
import datetime
from urllib.parse import quote, unquote
from django.utils import timezone
from django.contrib.auth import hashers
from django.utils.http import urlquote
from django.utils.encoding import iri_to_uri
from .models import User, Letter, Memo, UserForm
from .models import Board
from .models import BulletinBoard, TaskforceBoard, PublicBoard
from .models import BulletinEntry, TaskforceEntry, PublicEntry
from .models import BulletinComment, TaskforceComment, PublicComment
from .models import BulletinThumbnail, TaskforceThumbnail, PublicThumbnail 
from .models import BulletinFile, TaskforceFile, PublicFile, File
from .models import BulletinEntryForm, TaskforceEntryForm, PublicEntryForm
from .models import TaskforceBoardForm
from .models import Album, Photo, PhotoComment
from .models import AlbumForm, PhotoForm
from .models_base import Entry

# from .man_won_bbang import betting_list_now
import logging
logger = logging.getLogger(__name__)

import re

# import transformation

PublicBoardList = PublicBoard.objects.all()
PublicBoardDict = {}
for public_board in PublicBoardList:
    PublicBoardDict[public_board.name[:4]] = public_board

def classify(board):
    exist = True
    if board == 'bulletin':
        Board = BulletinBoard
        Entry = BulletinEntry
        Comment = BulletinComment
        Thumbnail = BulletinThumbnail
        File = BulletinFile
        EntryForm = BulletinEntryForm
    elif board == 'taskforce':
        Board = TaskforceBoard
        Entry = TaskforceEntry
        Comment = TaskforceComment
        Thumbnail = TaskforceThumbnail
        File = TaskforceFile
        EntryForm = TaskforceEntryForm
    elif board == 'public':
        Board = PublicBoard
        Entry = PublicEntry
        Comment = PublicComment
        Thumbnail = PublicThumbnail
        File = PublicFile
        EntryForm = PublicEntryForm
    else:
        exist = False

    return (exist, Board, Entry, Comment, Thumbnail, File, EntryForm)


def pagination(board, board_id, current_page, page_size = 20): # board_number가 0이면 최신글 목록

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    board_id = int(board_id)
    current_page = int(current_page) if current_page != '0' else 1
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    # 총 글 수와 entry list 구하기
    if board_id != 0:
        b = Board.objects.get(pk = board_id)
        count_entry = b.count_entry #Entry.objects.filter(board = ... ).count()
        entry_list = Entry.objects.filter(board = b).order_by('-arrangement')[no : (no + page_size)]
    else:
        count_entry = Entry.objects.count()
        entry_list = Entry.objects.all().order_by('-time_created')[no : (no + page_size)] # filter(board = board_number)

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)//page_size + 1

    # 페이지 리스트 만들기
#    real_list = []
    for e in entry_list:
        e.range = range(e.depth)

    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 4
    next_page = current_page + 4

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 4:
        next_page = 0
        last_page = 0
    if current_page <= 4:
        prev_page = 0
        first_page = 0

    return {'entry_list' : entry_list, 'current_page' : current_page, 'page_list' : page_list,
            'first_page' : first_page, 'last_page' : last_page, 'prev_page' : prev_page,
            'next_page' : next_page,}

def check_permission(request, board, current_board = None, mode = 'reading'):
    
    LevelDict = {'non':0, 'pre':1, 'asc':2, 'reg':3, 'exe':4, 'mgr':5}

    if board == 'public' and mode == 'reading':
        return True, None

    try:
        u = request.session['user_id']
        user = User.objects.get(user_id = u) 
    except KeyError:
        return False, redirect('yighub:login')
    except User.DoesNotExist: # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
        return False, redirect('yighub:logout',)

    if not current_board:
        if LevelDict[user.level] >= 1:
            return True, None
        else:
            messages.error(request, '접근 권한이 없습니다.')
            return False, render(request, 'yighub/error.html', )

    if mode == 'reading':
        if LevelDict[user.level] >= LevelDict[current_board.permission_reading]:
            return True, None
        else:
            messages.error(request, '접근 권한이 없습니다.')
            return False, render(request, 'yighub/error.html', )
    elif mode == 'writing':
        if LevelDict[user.level] >= LevelDict[current_board.permission_writing]:
            return True, None
        else:
            messages.error(request, '접근 권한이 없습니다.')
            return False, render(request, 'yighub/error.html', )
    else:
        raise 'invalid argument'

def get_board_list(board):

    if board == 'taskforce':
        board_list = TaskforceBoard.objects.filter(archive = False).order_by('-count_entry')
    elif board == 'bulletin':
        board_list = BulletinBoard.objects.all()
    else:
        board_list = None

    return board_list


class Introduction(TemplateView):
    template_name = "yighub/public_Introduction.html"


class Vision(TemplateView):
    template_name = "yighub/public_Vision.html"


class Activity(TemplateView):
    template_name = "yighub/public_Activity.html"


class History(TemplateView):
    template_name = "yighub/public_History.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()
        p = pagination("public", '4', current_page='0')
        for e in p['entry_list']:
            e.history = []
            months = e.content.split('\n')
            for m in months:
                month = m.split('-')[0][:-1]
                events = m.split('-')[1].split(', ')
                e.history.append({'month': month, 'events': events})
        context['page']=p
        return context


class Recruiting(TemplateView):
    template_name = "yighub/public_Recruiting.html"


class Apply(TemplateView):
    template_name="yighub/public_Apply.html"


class Schedule(TemplateView):
    template_name = "yighub/public_Schedule.html"


class FAQ(TemplateView):
    template_name = "yighub/public_FAQ.html"


class MemberProfile(TemplateView):
    template_name = "yighub/public_Member Profile.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        current_ordinal = User.objects.all().order_by('-ordinal')[0].ordinal
        p=pagination("public", "10", current_page=page)

        if page == '0':
            p['display_ordinal'] = current_ordinal
        else:
            p['display_ordinal'] = int(page)

        p['user_list'] = User.objects.filter(ordinal=p['display_ordinal']).order_by('name')
        p['ordinal_range'] = range(1, current_ordinal + 1)
        context['page']=p

        return context


class SIM_A(TemplateView):
    template_name = "yighub/public_simA.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        p=pagination("public", "11", current_page=page, page_size=10)
        context.update({'page':p, 'board_id': 11, "board": "public"})

        return context


class SIM_JS(TemplateView):
    template_name = "yighub/public_simJ.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        p=pagination("public", "71", current_page=page, page_size=10)
        context.update({'page':p, 'board_id': 71, "board": "public"})

        return context


class Gfund(TemplateView):
    template_name = "yighub/public_GFun.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        p=pagination("public", "92", current_page=page, page_size=10)
        context.update({'page':p, 'board_id': 71, "board": "public"})

        return context


class Sfund(TemplateView):
    template_name = "yighub/public_SFun.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        try:
            p=pagination("public", "98", current_page=page, page_size=10)
        except:
            context.update({'board_id': 98, "board": "public"})
        else:
            context.update({'page':p, 'board_id': 98, "board": "public"})

        return context


class Fund_detail(DetailView):
    template_name = "yighub/public_fund_detail.html"

    def get_context_data(self, **kwargs):
        context=super(DetailView, self).get_context_data()
        try:
            user=User.objects.get(id=self.request.user.pk)
        except:
            context['user']=None
        else:
            context['user']=user
        if "SIMA" in self.request.path:
            context['Fund_name']="SIM-A Fund"
        elif "SIMJS" in self.request.path:
            context['Fund_name']="SIM-JS Fund"
        elif "GFund" in self.request.path:
            context['Fund_name']="G Fund"
        elif "Universe" in self.request.path:
            context['Fund_name']="YIG Universe"
        else:
            context['Fund_name']="S Fund"

        return context

    def get_object(self):
        object = PublicEntry.objects.get(id=self.kwargs['pk'])
        object.downloads = []

        for f in object.files.all():
            f.filename = urlquote(f.name)
            object.downloads.append(f)

        return object


class YIG_Universe(TemplateView):
    template_name = "yighub/public_Universe.html"

    def get_context_data(self, page):
        context=super(TemplateView, self).get_context_data()
        p=pagination("public", "14", current_page=page, page_size=10)
        context.update({'page':p, 'board_id': 14, "board": "public"})

        return context


class Research(TemplateView):
    template_name = "yighub/public_Research.html"

    def get_context_data(self, page):
        context = super(TemplateView, self).get_context_data()
        p = pagination("public", "15", current_page=page, page_size=2)

        for e in p['entry_list']:
            e.downloads = []
            for f in e.files.all():
                f.filename = urlquote(f.name)
                e.downloads.append(f)
        context.update({'page': p, 'board_id': 15, "board": "public"})

        return context


class Contact(TemplateView):
    template_name = "yighub/public_Contact Us.html"


class TopBar_for_Visitor(TemplateView):
    template_name = "yighub/extends/TopBar_for_Visitor.html"


class SubTopBar_for_Visitor(TemplateView):
    template_name="yighub/extends/Sub_TopBar_For_Visitor.html"


def home(request):

    if 'user_id' not in request.session:
        logger.info('방문자가 홈페이지를 열었습니다.')
        return render(request, 'yighub/home_for_visitor.html', {'public_dict' : PublicBoardDict})
    else:
        u = request.session['user_id']
    try:
        user = User.objects.get(user_id = u)
    except User.DoesNotExist:
        logger.info('세션의 회원정보(%d)가 데이터베이스에 존재하지 않아 로그아웃 됩니다.' % u)
        return redirect(reverse('yighub:logout'))

    # 홈페이지를 열 때마다 마지막 방문날짜를 업데이트한다.
    user.last_login = timezone.now()
    user.save()
    
    if user.level == 'non':
        logger.info('비회원 %s(%d)님이 홈페이지를 열었습니다.' % (user.name, user.id))
        return render(request, 'yighub/home_for_visitor.html', {'public_dict' : PublicBoardDict, 'user' : user})

    bulletin_list = get_board_list('bulletin')
    taskforce_list = get_board_list('taskforce')

    news = []
    bulletin_news = BulletinEntry.objects.all().order_by('-time_created')[0:10]
    for b in bulletin_news:
        b.board_type = 'bulletin'
    news += bulletin_news
    taskforce_news = TaskforceEntry.objects.all().order_by('-time_created')[0:10]
    for t in taskforce_news:
        t.board_type = 'taskforce'
    news += taskforce_news
    news = sorted(news, key=lambda news: news.time_created, reverse=True)[:10]

    # memos = Memo.objects.all().order_by('-pk')[0:10]
    # news += bulletin_news
    # taskforce_news = TaskforceEntry.objects.all().order_by('-time_created')[0:10]
    # album_news = Album.objects.order_by('-newest_time')[:2]
    # for album in album_news:
    #     try:
    #         album.thumbnail = album.photos.all()[0]
    #     except:
    #         album.thumbnail = None
    #
    # today = datetime.datetime.now()
    # birthday_list = []
    # for member in User.objects.all():
    #     if member.level != 'non':
    #         if member.birthday:
    #             if member.birthday.month == today.month and member.birthday.day == today.day:
    #                 birthday_list.append(member)

    # logger.info('%s(%d)님이 홈페이지를 열었습니다.' % (user.name, user.id))

    return render(request, 'yighub/home_for_member.html', { 'user' : user, 'public_dict' : PublicBoardDict,
    'bulletin_list' : bulletin_list, 'taskforce_list' : taskforce_list, 'news' : news, 'boards_news': bulletin_news,
    'taskforce_news': taskforce_news },)


class home_member(TemplateView):
    template_name = "yighub/home_for_member.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()
        username=self.request.session['user_id']
        try:
            user = User.objects.get(user_id=username)
        except User.DoesNotExist:
            logger.info('세션의 회원정보(%d)가 데이터베이스에 존재하지 않아 로그아웃 됩니다.' % username)
            return redirect(reverse('yighub:logout'))
        # 홈페이지를 열 때마다 마지막 방문날짜를 업데이트한다.
        user.last_login = timezone.now()
        user.save()

        bulletin_list = get_board_list('bulletin')
        taskforce_list = get_board_list('taskforce')

        news = []
        bulletin_news = BulletinEntry.objects.all().order_by('-time_created')[0:10]
        for b in bulletin_news:
            b.board_type = 'bulletin'
        news += bulletin_news
        taskforce_news = TaskforceEntry.objects.all().order_by('-time_created')[0:10]
        for t in taskforce_news:
            t.board_type = 'taskforce'
        news += taskforce_news
        news = sorted(news, key=lambda news: news.time_created, reverse=True)[:10]

        context.update({'public_dict' : PublicBoardDict, 'bulletin_list' : bulletin_list, 'taskforce_list' : taskforce_list,
                        'news' : news, 'boards_news': bulletin_news, 'taskforce_news': taskforce_news})

        return context

#임시방편
class Topbar_member(TemplateView):
    template_name = "yighub/extends/TopBar_for_member.html"


####MEMBERS CLASS START########
class BoardsNews(TemplateView):
    template_name = "yighub/member_BoardsNews.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        # 권한 검사
        try:
            u = self.request.session['user_id']
            user = User.objects.get(user_id=u)
        except KeyError:
            return redirect('yighub:login')
        except User.DoesNotExist:  # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
            return redirect('yighub:logout', )

        if user.level == 'non':
            messages.error(self.request, '접근 권한이 없습니다.')
            return render(self.request, 'yighub/error.html', )

        p = pagination("bulletin", board_id=0, current_page=self.kwargs['pk'])
        board_list = get_board_list("bulletin")

        logger.info('%s(%d)님이 %s news를 열었습니다.' % (user.name, user.id, "bulletin"))
        context.update({'public_dict': PublicBoardDict, 'board': "bulletin", 'board_list': board_list,
                       'page': p})
        return context


class Column(TemplateView):
    template_name = "yighub/member_Column.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=19
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})

        return context



class Data(TemplateView):
    template_name = "yighub/member_data.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=18
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})

        return context


class Portfolio(TemplateView):
    template_name = "yighub/member_Portfolio.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=20
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})
        return context


class Analysis(TemplateView):
    template_name = "yighub/member_analysis.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=21
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})
        return context


class Notice(TemplateView):
    template_name = "yighub/member_notice.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=22
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})
        return context


class Etc(TemplateView):
    template_name = "yighub/member_etc.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()

        board="bulletin"
        board_id=23
        page='0'

        # board 분류
        exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
        if exist == False:
            raise Http404

        try:
            current_board = Board.objects.get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404

        p = pagination(board, board_id, current_page='0')
        board_list = get_board_list(board)

        # 권한 검사
        permission = check_permission(self.request, board, current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        if u:
            logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
        else:
            logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

        context.update({'public_dict': PublicBoardDict, 'board': board, 'board_list': board_list,
                       'current_board': current_board, 'page': p})
        return context


class TaskforceNews(TemplateView):
    template_name = "yighub/member_TaskforceNews.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()
        # 권한 검사
        try:
            u = self.request.session['user_id']
            user = User.objects.get(user_id=u)
        except KeyError:
            return redirect('yighub:login')
        except User.DoesNotExist:  # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
            return redirect('yighub:logout', )

        if user.level == 'non':
            messages.error(self.request, '접근 권한이 없습니다.')
            return render(self.request, 'yighub/error.html', )

        p = pagination("taskforce", board_id=0, current_page=self.kwargs['pk'])
        board_list = get_board_list("taskforce")

        logger.info('%s(%d)님이 %s news를 열었습니다.' % (user.name, user.id, "bulletin"))
        context.update({'public_dict': PublicBoardDict, 'board': "taskforce", 'board_list': board_list,
                       'page': p})
        return context


class Taskforce(TemplateView):
    template_name = "yighub/member_Taskforce.html"

    def get_context_data(self, **kwargs):
        context=super(TemplateView, self).get_context_data()
        try:
            current_board = Board.objects.get(pk=self.kwargs['board_id'])
        except Board.DoesNotExist:
            raise Http404

        p = pagination("taskforce", self.kwargs['board_id'], current_page=self.kwargs['page'])
        board_list = get_board_list("taskforce")

        # 권한 검사
        permission = check_permission(self.request, "taskforce", current_board)
        if permission[0] == False:
            return permission[1]
        try:
            u = User.objects.get(user_id=self.request.session['user_id'])
        except:
            u = None

        board="taskforce"
        context.update({'user': u, 'board_list': board_list, 'current_board': current_board, 'page': p
                        ,'board': board, 'board_id': int(self.kwargs['board_id'])})
        return context


def all_news(request, page):

    permission = check_permission(request, 'memo')
    if permission[0] == False:
        return permission[1] 
    u = User.objects.get(user_id = request.session['user_id'])
    
    bulletin_list = get_board_list('bulletin')
    taskforce_list = get_board_list('taskforce')

    current_page = int(page)
    page_size = 20
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    count_entry = TaskforceEntry.objects.count() + BulletinEntry.objects.count()
    news = []
    bulletin_news = BulletinEntry.objects.all().order_by('-time_created')[ :(no + page_size)]
    for b in bulletin_news:
        b.board_type = 'bulletin'
    news += bulletin_news
    taskforce_news = TaskforceEntry.objects.all().order_by('-time_created')[ :(no + page_size)]
    for t in taskforce_news:
        t.board_type = 'taskforce'
    news += taskforce_news
    news = sorted(news, key = lambda news: news.time_created, reverse = True)
    news = news[no : (no + page_size)]

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)//page_size + 1

    # 페이지 리스트 만들기
    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 5
    next_page = current_page + 5

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 5:
        next_page = 0
        last_page = 0
    if current_page <= 5:
        prev_page = 0
        first_page = 0

    p = {'entry_list' : news,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

    return render(request, 'yighub/all_news.html', 
        { 'user' : u,
          'public_dict' : PublicBoardDict,
          'bulletin_list' : bulletin_list,
          'taskforce_list' : taskforce_list,
          'page' : p,
          }
    )

def news(request, board, page):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False or Board == PublicBoard:
        raise Http404

    # 권한 검사
    try:
        u = request.session['user_id']
        user = User.objects.get(user_id = u) 
    except KeyError:
        return redirect('yighub:login')
    except User.DoesNotExist: # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
        return redirect('yighub:logout',)
    if user.level == 'non':
        messages.error(request, '접근 권한이 없습니다.')
        return render(request, 'yighub/error.html', )

    p = pagination(board, board_id = 0, current_page = page)
    board_list = get_board_list(board)

    logger.info('%s(%d)님이 %s news를 열었습니다.' % (user.name, user.id, board))
    return render(request, 'yighub/news.html',
        {'user': user, 'public_dict' : PublicBoardDict, 'board': board, 'board_list': board_list, 'page': p}
        )

def listing(request, board, board_id, page = '0'):    # url : yig.in/yighub/board/1/page/3

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        current_board = Board.objects.get(pk = board_id)
    except Board.DoesNotExist:
        raise Http404

    if current_board.name in ('Research',):
        p = pagination(board, board_id, current_page = page, page_size = 3)
    elif current_board.name in ('simA', 'simB', 'simV', 'simH', 'simJ', 'GFun', 'SFun', 'Universe'):
        p = pagination(board, board_id, current_page = page, page_size = 1)        
    else:
        p = pagination(board, board_id, current_page = page)
    board_list = get_board_list(board)

    # 권한 검사
    permission = check_permission(request, board, current_board)
    if permission[0] == False:
        return permission[1]
    try:
        u = User.objects.get(user_id = request.session['user_id'])
    except:
        u = None

    if u:
        logger.info('%s(%d)님이 %s 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, current_board.name, page))
    else:
        logger.info('방문자가 %s 게시판 %s 페이지를 열었습니다.' % (current_board.name, page))

    if board == 'public' and current_board.name!="Introduction":
        if current_board.name == 'Member Profile':
            current_ordinal = User.objects.all().order_by('-ordinal')[0].ordinal
            if page == '0':
                p['display_ordinal'] = current_ordinal
            else:
                p['display_ordinal'] = int(page)

            p['user_list'] = User.objects.filter(ordinal = p['display_ordinal']).order_by('name')
            p['ordinal_range'] = range(1, current_ordinal+1)

        for e in p['entry_list']:
            e.downloads = []
            for f in e.files.all():
                f.filename = urlquote(f.name)
                e.downloads.append(f)

        return render(request, 'yighub/public_' + current_board.name + '.html', 
            {'user': u, 'public_dict' : PublicBoardDict, 'board': board, 'board_list': board_list,
             'current_board': current_board, 'page': p})

    return render(request, 'yighub/listing.html',
        {'user': u, 'public_dict' : PublicBoardDict, 'board': board, 'board_list': board_list,
         'current_board': current_board, 'page': p})

    # if board_id:
    #     b = Board.objects.get(pk = board_id)
    # else:
    #     class b:
    #         pass
    #     b.name = '최신글 목록'

    # if b.name == '최신글 목록':
    #     return render(request, 'yighub/news.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # if b.name == 'Board':
    #     return render(request, 'yighub/board.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # if b.name == 'Notice':
    #     return render(request, 'yighub/notice.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # if b.name == 'Company Analysis':
    #     return render(request, 'yighub/company analysis.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # if b.name == 'Portfolio':
    #     return render(request, 'yighub/portfolio.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # if b.name == 'Column':
    #     return render(request, 'yighub/column.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    # else:
    #     return render(request, 'yighub/taskforce.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })

def create_taskforce(request):

    # 권한 검사
    permission = check_permission(request, 'taskforce', mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = TaskforceBoardForm(request.POST)
        if form.is_valid():

            t = form.save(commit = False)            
            t.permission_reading = 'pre'
            t.permission_writing = 'pre'
            t.save()

            logger.info('%s(%d)님이 새 taskforce를 만들었습니다: "%s"(%d)' % (u.name, u.id, t.name, t.id))

            return redirect('yighub:member_Taskforce_News', pk=0 )
    else:
        form = TaskforceBoardForm()

    logger.info('%s(%d)님이 taskforce 만들기 페이지를 열었습니다.' % (u.name, u.id))
    return render(request, 'yighub/create_taskforce.html', {'user' : u, 'public_dict' : PublicBoardDict, 'form' : form})

def edit_taskforce(request, taskforce_id): # 여기서 archive로 넘기기도 처리. 삭제는 일단 구현 안함. 게시글이 하나도 없을 때만 가능.

    try:
        t = TaskforceBoard.objects.get(pk = taskforce_id)
    except TaskforceBoard.DoesNotExist:
        return Http404

    # 권한 검사
    permission = check_permission(request, 'taskforce', current_board = t, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = TaskforceBoardForm(request.POST, instance = t)
        if form.is_valid():

            t = form.save(commit = False)
            if 'to_archive' in request.POST:
                if request.POST['to_archive']:
                    t.archive = True
            if 'to_list' in request.POST:
                if request.POST['to_list']:
                    t.archive = False
            t.save()

            logger.info('%s(%d)님이 %s taskforce(%d)를 수정했습니다.' % (u.name, u.id, t.name, t.id))
            return redirect('yighub:member_Taskforce_News', pk=1)
    else:
        form = TaskforceBoardForm(instance = t)

    logger.info('%s(%d)님이 %s taskforce(%d) 수정하기 페이지를 열었습니다.' % (u.name, u.id, t.name, t.id))
    return render(request, 'yighub/edit_taskforce.html', {'user' : u, 'public_dict' : PublicBoardDict, 'form' : form, 'current_taskforce' : t})

def taskforce_archive(request):

    # 권한 검사
    permission = check_permission(request, 'taskforce', mode = 'writing')
    if permission[0] == False:
        return permission[1]

    taskforce_list = TaskforceBoard.objects.filter(archive = True).order_by('-newest_time')

    u = User.objects.get(user_id = request.session['user_id'])
    board_list = get_board_list('taskforce')

    logger.info('%s(%d)님이 taskforce 아카이브를 열었습니다.' % (u.name, u.id))

    return render(request, 'yighub/taskforce_archive.html', 
        {'user' : u, 
        'public_dict' : PublicBoardDict, 
        'board' : 'taskforce', 
        'board_list' : board_list,
        'taskforce_list' : taskforce_list
        })

def read(request, board, entry_id,):
        
    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, board, e.board)
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])
    
    e.count_view += 1
    e.save()

    thumbnails = e.thumbnails.all()
    files = e.files.all() #File.objects.filter(entry = e)
    for f in files:
        f.filename = urlquote(f.name)
    recommendations = e.recommendation.all()
    count_recommendation = e.recommendation.count()
    comments = e.comments.order_by('arrangement')
    current_board = e.board
    board_list = get_board_list(board)

    logger.info('%s(%d)님이 게시글을 읽었습니다: "%s"(%d)' % (u.name, u.id, e.title, e.id))
    return render(request, 'yighub/read.html',
      {'user' : u,
      'public_dict' : PublicBoardDict, 
      'board' : board,
      'board_list' : board_list,
      'current_board' : current_board,
      'entry' : e,
      'thumbnails' : thumbnails,
      'files' : files,
      'recommendations' : recommendations,
      'count_recommendation' : count_recommendation,
      'comments' : comments,
      },
      )

def create(request, board, board_id = None):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    if board_id:
        try:
            current_board = Board.objects.get(pk=board_id)

        except Board.DoesNotExist:
            raise Http404
    else:
        current_board = None

    # 권한 검사
    permission = check_permission(request, board, current_board, mode = 'writing')
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = EntryForm(request.POST, request.FILES)
        if form.is_valid():
            
            current_board = Board.objects.get(pk = request.POST['board'])

            # arrangement 할당
            try:
                last_entry = Entry.objects.filter(board = current_board).order_by('-arrangement')[0]
            except IndexError:
                arrangement = 1000
            else:
                arrangement = (last_entry.arrangement//1000 + 1) * 1000

            # 글을 저장한다.
            e = form.save(commit = False)
            e.creator = User.objects.get(user_id = request.session['user_id'])
            e.time_created = timezone.now()
            e.time_last_modified = e.time_created # 둘 다 timezone.now()로 했을 시 수정 안한 글에서도 마지막 수정한 날짜가 뜬다.
            e.arrangement = arrangement
            e.save()

            # 썸네일을 저장한다.
            thumbnails = request.FILES.getlist('thumbnails')
            for thumbnail in thumbnails:
                t = Thumbnail(entry = e, name = thumbnail.name, thumbnail = thumbnail)
                t.save()
            
            # 여러 파일들을 저장한다.
            files = request.FILES.getlist('files')
            for file in files:
                f = File(entry = e, name = file.name, file = file)
                f.save()
            
            # 게시판 정보를 업데이트한다.
            b = Board.objects.get(pk = request.POST['board'])
            b.count_entry += 1
            b.newest_entry = e.id
            b.newest_time = e.time_last_modified
            b.save()

            logger.info('%s(%d)님이 %s 게시판(%d)에 게시글을 작성했습니다: "%s"(%d)' % (u.name, u.id, current_board.name, current_board.id, e.title, e.id))

            if board=="bulletin":
                return redirect('yighub:member_Boards_News', pk=0)
            elif board=="taskforce":
                return redirect('yighub:member_Taskforce_News', pk=0)
            else:
                return redirect('yighub:home_for_member', pk=0)
    else:
        if board_id:
            form = EntryForm(initial = {'board' : current_board})
        else:
            form = EntryForm()

    board_list = get_board_list(board)

    if current_board:
        logger.info('%s(%d)님이 %s 게시판 글쓰기 페이지를 열었습니다.' % (u.name, u.id, current_board.name))
    else:
        logger.info('%s(%d)님이 %s 글쓰기 페이지를 열었습니다.' % (u.name, u.id, board))

    return render(request, 'yighub/create.html', 
        {'user' : u, 
        'public_dict' : PublicBoardDict, 
        'board' : board,
        'board_list' : board_list,
        'current_board' : current_board,
        'form' : form, }
        )

def edit(request, board, entry_id):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        return Http404
        #messages.error(request, 'the entry does not exist')
        #return render(request, 'yighub/error.html', )

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = EntryForm(request.POST, instance = e)
        if form.is_valid():

            e = form.save(commit = False)
            e.time_last_modified = timezone.now()
            e.save()
            
            for t in e.thumbnails.all():
                try:
                    string = 'delete_thumbnail_' + str(t.id)
                    request.POST[string]
                except KeyError:
                    pass
                else:
                    t.thumbnail.delete()
                    t.delete()

            thumbnails = request.FILES.getlist('thumbnails')
            for thumbnail in thumbnails:
                t = Thumbnail(entry = e, name = thumbnail.name, thumbnail = thumbnail)
                t.save()

            for f in e.files.all():
                try:
                    string = 'delete_file_' + str(f.id)
                    request.POST[string]
                except KeyError:
                    pass
                else:
                    f.file.delete()
                    f.delete()
            
            files = request.FILES.getlist('files')
            for file in files:
                f = File(entry = e, name = file.name, file = file)
                f.save()

            # 게시판 정보를 업데이트한다. - 필요한가?
            ##b = e.board
            ##b.newest_entry
            ##b.newest_time
            logger.info('%s(%d)님이 게시글을 수정했습니다: "%s"(%d)' % (u.name, u.id, e.title, e.id))
            return redirect('yighub:read', board=board, entry_id = entry_id) #HttpResponseRedirect(reverse('yighub.views.read', args = (entry_id, )))
            
    else:
        form = EntryForm(
            initial = {'user' : u,
            'board' : e.board, 'title' : e.title, 'content' : e.content, 'notice' : e.notice}
            )
    
    thumbnails = e.thumbnails.all()
    files = e.files.all()
    for f in files:
        f.filename = urlquote(f.name)
    board_list = get_board_list(board)
    current_board = e.board

    logger.info('%s(%d)님이 게시글 수정 페이지를 열었습니다.' % (u.name, u.id))
    return render(request, 'yighub/edit.html', 
        {'user' : u, 
        'public_dict' : PublicBoardDict, 
        'board' : board,
        'board_list' : board_list,
        'current_board' : current_board,
        'form' : form, 'thumbnails' : thumbnails, 'files' : files, 'entry_id' : entry_id },)


def delete(request, board, entry_id):
    
    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if u == e.creator:
        thumbnails = e.thumbnails.all()
        for t in thumbnails:
            t.thumbnail.delete()

        files = e.files.all()
        for f in files:
            f.file.delete()

        # 게시판 정보를 업데이트한다.
        b = e.board
        if e.id == b.newest_entry:
            if b.count_entry > 1: 
                prev_entry = Entry.objects.filter(board = b).order_by('-arrangement')[1] # edit과 reply를 포함하면 time_last_modified로.
                b.newest_entry = prev_entry.id
                b.newest_time = prev_entry.time_created
            else: # 게시판에 글이 하나 남았을 때
                b.newest_entry = None
                b.newest_time = None
        b.count_entry -= 1
        b.save()

        logger.info('%s(%d)님이 게시글을 삭제했습니다: "%s"(%d)' % (u.name, u.id, e.title, e.id))
        e.delete()
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )
        #return render(request, 'yighub/error.html', {'error' : 'invalid approach'})
    return HttpResponseRedirect(reverse('yighub:home', ))

def reply(request, board, entry_id): # yig.in/entry/12345/reply     

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        parent = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        raise Http404
    
    # 권한 검사
    permission = check_permission(request, board, parent.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = EntryForm(request.POST, request.FILES)
        if form.is_valid():
            
            current_depth = parent.depth + 1
            current_arrangement = parent.arrangement - 1
            p = entry_id
            scope = Entry.objects.filter(board = parent.board).filter(arrangement__gt = (current_arrangement//1000) * 1000).filter(arrangement__lte = current_arrangement)
            
            while True:
                try:
                    q = scope.filter(parent = p).order_by('arrangement')[0] 
                except IndexError:
                    break
                else:
                    current_arrangement = q.arrangement - 1
                    p = q.id
            
            to_update = Entry.objects.filter(board = parent.board).filter(arrangement__gt = (current_arrangement//1000) * 1000 ).filter(arrangement__lte = current_arrangement)
            for e in to_update:
                e.arrangement -= 1
                e.save()

            reply = form.save(commit = False)
            reply.arrangement = current_arrangement
            reply.depth = current_depth
            reply.parent = entry_id
            reply.creator = User.objects.get(user_id = request.session['user_id'])
            reply.time_created = timezone.now()
            reply.time_last_modified = timezone.now()
            reply.save()

            thumbnails = request.FILES.getlist('thumbnails')
            for thumbnail in thumbnails:
                t = Thumbnail(entry = reply, name = thumbnail.name, thumbnail = thumbnail)
                t.save()

            files = request.FILES.getlist('files')
            for file in files:
                f = File(entry = reply, name = file.name, file = file)
                f.save()

            # 게시판 정보를 업데이트한다.
            b = reply.board
            b.newest_entry = reply.id
            b.newest_time = reply.time_created
            b.count_entry += 1
            b.save()

            logger.info('%s(%d)님이 게시글(%d)에 답글을 달았습니다: "%s"(%d)' % (u.name, u.id, parent.id, reply.title, reply.id))
            return HttpResponseRedirect(reverse('yighub:home'))
    else:
        form = EntryForm(initial = {'board' : parent.board}) # board 빼고 보내기

    board_list = get_board_list(board)
    b = parent.board

    logger.info('%s(%d)님이 게시글(%d)에 답글 달기 페이지를 열었습니다.' % (u.name, u.id, parent.id))
    return render(request, 'yighub/reply.html', 
        {'user' : u,
        'public_dict' : PublicBoardDict, 
        'board' : board,
        'board_list' : board_list,
        'current_board' : b,
        'form' : form, 'parent' : entry_id}, 
        ) 

def recommend(request, board, entry_id):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])
    if u in e.recommendation.all():
        messages.error(request, 'You already recommend this')
        return render(request, 'yighub/error.html', )
    e.recommendation.add(u)
    e.count_recommendation += 1
    e.save()

    logger.info('%s(%d)님이 게시글을 추천했습니다: "%s"(%d)' % (u.name, u.id, e.title, e.id))
    return redirect('yighub:read', board = board, entry_id = entry_id)

def delete_recommend(request, board, entry_id):
    
    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]
    
    u = User.objects.get(user_id = request.session['user_id'])
    if u in e.recommendation.all():
        e.count_recommendation -= 1
        e.recommendation.remove(u)
        e.save()

        logger.info('%s(%d)님이 게시글 추천을 취소했습니다: "%s"(%d)' % (u.name, u.id, e.title, e.id))
        return redirect('yighub:read', board = board, entry_id = entry_id)
    else:
        messages.error(request, 'You have not recommended this')
        return render(request, 'yighub/error.html', )

def comment(request, board, entry_id):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        e = Entry.objects.get(pk = entry_id)
        try:
            newest_comment = Comment.objects.order_by('-arrangement')[0]
        except IndexError:
            arrangement = 0
        else:
            arrangement = (newest_comment.arrangement//1000 + 1) * 1000
        c = Comment(entry = e,
                    content = request.POST['content'],
                    creator = u,
                    time_created = timezone.now(),
                    arrangement = arrangement,
                    )
        c.save()
        e.count_comment += 1
        e.save()

        logger.info('%s(%d)님이 게시글(%d)에 댓글을 달았습니다: "%s"(%d)' % (u.name, u.id, e.id, c.content, c.id))
        return redirect('yighub:read', board = board, entry_id = entry_id) # HttpResponseRedirect(reverse('yighub.views.read', args = (entry_id)))
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def reply_comment(request, board, entry_id):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    if request.method == 'POST':
        e = Entry.objects.get(pk = entry_id)
        u = User.objects.get(user_id = request.session['user_id'])

        parent = Comment.objects.get(pk = int(request.POST['comment_id'])) # int error ?
        current_depth = parent.depth + 1
        current_arrangement = parent.arrangement + 1

        p = request.POST['comment_id']
        scope = Comment.objects.filter(entry = e).filter(arrangement__gte = current_arrangement).filter(arrangement__lt = (parent.arrangement//1000 + 1) * 1000)

        while True:
            try:
                q = scope.filter(parent = p).order_by('arrangement')[0] 
            except IndexError:
                break
            else:
                current_arrangement = q.arrangement + 1
                p = q.pk

        to_update = Comment.objects.filter(arrangement__gte = current_arrangement).filter(arrangement__lt = (current_arrangement//1000 + 1) * 1000 )
        for c in to_update:
            c.arrangement += 1
            c.save()

        reply_comment = Comment(entry = e,
                                content = request.POST['content'], 
                                creater = u, 
                                time_created = timezone.now(),
                                arrangement = current_arrangement,
                                depth = current_depth,
                                parent = request.POST['comment_id'],
                                )                                              
        reply_comment.save()

        return HttpResponseRedirect(reverse('yighub:read', board = board, entry_id = entry_id))
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def recommend_comment(request, board, entry_id, comment_id):

    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id) 
        c = Comment.objects.get(pk = comment_id)
    except (Entry.DoesNotExist, Comment.DoesNotExist): # comma로 묶는게 어떤 의미인가?
        raise Http404    

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])
    if u in c.recommendation.all():
        messages.error(request, 'You already recommend this')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))
    c.recommendation.add(u)
    c.count_recommendation += 1
    c.save()

    logger.info('%s(%d)님이 댓글을 추천했습니다: "%s"(%d)' % (u.name, u.id, c.content, c.id))
    return redirect('yighub:read', board = board, entry_id = entry_id)

def delete_comment(request, board, entry_id, comment_id):
    
    # board 분류
    exist, Board, Entry, Comment, Thumbnail, File, EntryForm = classify(board)
    if exist == False:
        raise Http404

    try:
        e = Entry.objects.get(pk = entry_id)
        c = Comment.objects.get(pk = comment_id)
    except (Entry.DoesNotExist, Comment.DoesNotExist):
        raise Http404

    # 권한 검사
    permission = check_permission(request, board, e.board, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if u == c.creator:
        e.count_comment -= 1
        e.save()

        logger.info('%s(%d)님이 게시글(%d)에서 댓글을 삭제했습니다: "%s"(%d)' % (u.name, u.id, e.id, c.content, c.id))

        c.delete()

    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )
        #return render(request, 'yighub/error.html', {'error' : 'invalid approach'})
    return redirect('yighub:read', board=board, entry_id=entry_id)


def join(request):
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                User.objects.get(user_id = request.POST['user_id'])
            except User.DoesNotExist:
                if request.POST['password'] == request.POST['password_check']:
                    regex = re.compile(r'\d{3}-\d{4}-\d{4}')
                    if not request.POST['phone_number'] or regex.match(request.POST['phone_number']):

                        f = form.save(commit = False)
                        f.password = hashers.make_password(request.POST['password'])
                        f.date_joined = timezone.now()
                        f.last_login = timezone.now()
                        f.level = 'non'
                        

                        f.profile = request.FILES['profile'] if 'profile' in request.FILES else None
                        f.avatar = request.FILES['avatar'] if 'avatar' in request.FILES else None
                        
                        f.save()

                        u = User.objects.get(user_id = request.POST['user_id'])
                        request.session['user_id'] = u.user_id

                        logger.info('%s(%d)님이 가입했습니다.' % (u.name, u.id))

                        return redirect('yighub:home', )
                    else:
                        messages.error(request, 'phone number must be a form of "010-1234-1234"')
                else:
                    messages.error(request, 'please check your password.')
            else:
                    messages.error(request, 'already used id. please change your id.')
    else:
        form = UserForm()

    return render(request, 'yighub/join.html', {'public_dict' : PublicBoardDict, 'form' : form}, context_instance = RequestContext(request))

def edit_profile(request, first_login = False):

    try:
        u = User.objects.get(user_id = request.session['user_id'])
    except User.DoesNotExist:
        raise Http404

    if request.method == 'POST':

        if u.user_id != request.POST['user_id']:
            try:
                User.objects.get(user_id = request.POST['user_id'])
            except User.DoesNotExist:
                pass
            else:
                messages.error(request, 'already used id. please change your id.')
                form = UserForm(request.POST, )
                return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )

        if not first_login:
            if hashers.check_password(request.POST['password'], u.password):
                pass
            else:
                messages.error(request, 'please enter your old password.')
                form = UserForm(request.POST, )
                return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )

            if request.POST['new_password']:
                if request.POST['new_password'] == request.POST['password_check']:
                    pass
                else:
                    messages.error(request, 'please check your new password.')
                    form = UserForm(request.POST, )
                    return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )
        else:
            if request.POST['password'] == request.POST['password_check']:
                pass
            else:
                messages.error(request, 'please check your password.')
                form = UserForm(request.POST, )
                return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )

        if request.POST['phone_number']:
            regex = re.compile(r'\d{3}-\d{4}-\d{4}')
            if not regex.match(request.POST['phone_number']):
                messages.error(request, 'phone number must be a form of "010-1234-1234"')
                form = UserForm(request.POST, )
                return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )

        form = UserForm(request.POST, request.FILES, instance = u)
        if form.is_valid():

            f = form.save(commit = False)

            if not first_login:
                if request.POST['new_password']:
                    f.password = hashers.make_password(request.POST['new_password'])
                else:
                    f.password = hashers.make_password(request.POST['password'])
            else:
                f.password = hashers.make_password(request.POST['password'])
            f.profile = request.FILES['profile'] if 'profile' in request.FILES else u.profile
            f.avatar = request.FILES['avatar'] if 'avatar' in request.FILES else u.avatar

            f.save()

            u = User.objects.get(user_id = request.POST['user_id'])
            request.session['user_id'] = u.user_id

            logger.info('%s(%d)님이 프로필을 수정했습니다.' % (u.name, u.id))
            return redirect('yighub:home', )
    else:
        form = UserForm(instance = u, )

    logger.info('%s(%d)님이 프로필 수정 페이지를 열었습니다.' % (u.name, u.id))
    return render(request, 'yighub/edit_profile.html', {'user':u, 'public_dict' : PublicBoardDict, 'form' : form, 'first_login' : first_login}, )

def delete_profile(request):
    pass

def login(request):
    request.session.set_test_cookie()
    logger.info('로그인 페이지를 열었습니다.')
    return render(request, 'yighub/login.html', {'public_dict' : PublicBoardDict})
    
def login_check(request):
    try:
        u = User.objects.get(user_id = request.POST['user_id'])
    except User.DoesNotExist:
        logger.info('로그인이 실패했습니다.')
        messages.error(request, 'incorrect user id')
        return render(request, 'yighub/login.html', {'public_dict' : PublicBoardDict})

    if request.session.test_cookie_worked():

        if u.password == ' ':
            u.password = hashers.make_password(request.POST['password'])
            u.save()
            request.session['user_id'] = u.user_id

            logger.info('%s(%d)님이 처음 로그인했습니다.' % (u.name, u.id))

            return redirect('yighub:first_login',)

        if hashers.check_password(request.POST['password'], u.password):
            request.session['user_id'] = u.user_id

            logger.info('%s(%d)님이 로그인했습니다.' % (u.name, u.id))

            return HttpResponseRedirect(reverse('yighub:home_for_member'))
        else:
            messages.error(request, 'password does not correct') # send message 
            logger.info('%s(%d)님이 로그인 도중 비밀번호를 잘못 입력했습니다.' % (u.name, u.id))
            return render(request, 'yighub/login.html', {'public_dict' : PublicBoardDict})
    else:
        # send message about cookie
        messages.error(request, 'please enable cookie')
        return render(request, 'yighub/login.html', {'public_dict' : PublicBoardDict})

def logout(request):
    u = User.objects.get(user_id = request.session['user_id'])
    logger.info('%s(%d)님이 로그아웃했습니다.' % (u.name, u.id))
    request.session.flush() # exact functionality of flush method? after flush, home_for_visitor is presenting?
    return HttpResponseRedirect(reverse('yighub:home'))

def send(request):
    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES)
        if form.is_valid():

            s = form.save(commit = False)
            s.sender = User.objects.get(user_id = request.session['user_id'])
            s.file_name = request.FILES['file'].name
            s.save()

            return redirect('yighub.views.receive', )
    else:
        form = LetterForm()

    return render(request, 'yighub/send.html', {'form' : form}, context_instance = RequestContext(request))
 
         
def letters(request):
    u = request.POST['user']
    letters = Letter.objects.filter(receiver = u)

    # 페이지 넘기기 설정하기

    return render(request, 'yighub/letters.html', {'letters' : letters, })

def receive(request, letter_id): 

    if check_permission(request):
        pass

    try:
        l = Letter.objects.get(pk = letter_id)
    except Letter.DoesNotExist:
        raise Http404
    
    u = request.POST['user']
    
    if l.receiver == u:
        l.read = True
        l.save()
        return render(request, 'yighub/receive.html', {'letter' : l})
    else:
        messages.error(request, 'Not Yo')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))

def memo(request, page = 1):
    
    permission = check_permission(request, 'memo')
    if permission[0] == False:
        return permission[1] 
    u = User.objects.get(user_id = request.session['user_id'])
    
    bulletin_list = get_board_list('bulletin')
    taskforce_list = get_board_list('taskforce')

    current_page = int(page)
    page_size = 20
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    count_entry = Memo.objects.count()
    memo_list = Memo.objects.all().order_by('-pk')[no : (no + page_size)] # filter(board = board_number)

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)//page_size + 1

    # 페이지 리스트 만들기
    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 5
    next_page = current_page + 5

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 5:
        next_page = 0
        last_page = 0
    if current_page <= 5:
        prev_page = 0
        first_page = 0

    p = {'memo_list' : memo_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

    logger.info('%s(%d)님이 메모 게시판 %s 페이지를 열었습니다.' % (u.name, u.id, page))

    return render(request, 'yighub/memo.html',
        {'user': u, 'public_dict' : PublicBoardDict, 
        'bulletin_list' : bulletin_list, 
        'taskforce_list' : taskforce_list, 'page': p})

def create_memo(request):
    if request.method == 'POST':

        u = User.objects.get(user_id = request.session['user_id'])

        m = Memo(memo = request.POST['memo'],
                 creator = u,
                 time_created = timezone.now(),
                )
        m.save()
        
        logger.info('%s(%d)님이 메모를 남겼습니다: "%s"(%d)' % (u.name, u.id, m.memo, m.id))

        return HttpResponseRedirect(request.POST['path']) # 왔던 곳으로 되돌리기 위해 # redirect('yighub:home', ) 
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))

def delete_memo(request, memo_id):

    try:
        m = Memo.objects.get(pk = memo_id)
    except Memo.DoesNotExist:
        raise Http404

    u = User.objects.get(user_id = request.session['user_id'])

    if u == m.creator:
        logger.info('%s(%d)님이 메모를 삭제했습니다: "%s"(%d)' % (u.name, u.id, m.memo, m.id))
        m.delete()

    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )
        #return render(request, 'yighub/error.html', {'error' : 'invalid approach'})
    return HttpResponseRedirect(reverse('yighub:home', ))

def albums(request, page = 1):
    
    board = 'albums'

    # 권한 검사
    permission = check_permission(request, board, )
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])
    
    page_size = 12
    current_page = int(page) if page != '0' else 1
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    count_album = Album.objects.count()
    album_list = Album.objects.order_by('-newest_time')[no : (no + page_size)]

    albums = []
    for album in album_list:
        try:
            albums += [{'album':album, 'thumbnail':album.photos.all()[0]}]
        except:
            albums += [{'album':album, 'thumbnail':None}]

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_album - 1)//page_size + 1

    # 페이지 리스트 만들기
    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 5
    next_page = current_page + 5

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 4:
        next_page = 0
        last_page = 0
    if current_page <= 4:
        prev_page = 0
        first_page = 0

    p = {'album_list' : album_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

    logger.info('%s(%d)님이 앨범 목록 %s 페이지를 열었습니다.' % (u.name, u.id, page))
    return render(request, 'yighub/albums.html', {'user':u, 'public_dict' : PublicBoardDict, 'albums':albums, 'page':p})

def photos(request, album_id):
    
    board = 'albums'

    # 권한 검사
    permission = check_permission(request, board, )
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])
    
    album = Album.objects.get(pk = album_id)
    album.count_view += 1
    album.save()
    photos = album.photos.all()
    # template과 model의 분리를 위해 여기서 처리해야 하지만, 일단 이번엔 template에서 시도해본다. 되긴 된다. 
    #for p in photos:
    #    p.recommendations = p.recommendation.all()
    #    p.comment_list = p.comments.all()

    logger.info('%s(%d)님이 %s 앨범(%d)을 열었습니다.' % (u.name, u.id, album.name, album.id))
    return render(request, 'yighub/photos.html', {'user':u, 'public_dict' : PublicBoardDict, 'album':album, 'photos':photos, })

def create_album(request,):
    
    # 권한 검사
    permission = check_permission(request, 'albums')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
        form = AlbumForm(request.POST)
        if form.is_valid():

            a = form.save(commit = False)            
            a.newest_time = timezone.now() # 앨범 목록에서 맨 밑으로 내려가게 하지 않기 위해
            a.permission_reading = 'pre'
            a.permission_writing = 'pre'
            a.save()

            logger.info('%s(%d)님이 새 앨범을 만들었습니다: "%s"(%d)' % (u.name, u.id, a.name, a.id))

            return redirect('yighub:photos', album_id = a.id)
    else:
        form = AlbumForm()

    logger.info('%s(%d)님이 앨범 만들기 페이지를 열었습니다.' % (u.name, u.id))
    return render(request, 'yighub/create_album.html', {'user' : u, 'public_dict' : PublicBoardDict, 'form' : form})

def edit_album(request,):
    pass

def create_photos(request, album_id):

    try:
        a = Album.objects.get(pk = album_id)
    except Album.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, 'albums', a, mode = 'writing')
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':
            
            # 글을 저장한다.
        for k in range(int(request.POST['size'])):
            if 'photo_'+str(k) in request.FILES:
                p = Photo()
                p.album = a
                p.photo = request.FILES['photo_'+str(k)]
                p.description = request.POST['description_'+str(k)]
                p.photographer = u
                p.time_created = timezone.now()
                p.time_last_modified = p.time_created # timezone.now()를 하면 time_created와 미묘하게 달라진다.
                p.save()
                # 게시판 정보를 업데이트한다.
                a.count_photo += 1
                a.newest_time = p.time_created # 정렬은 만들어진 시간 순서 대로.
                a.save()

                logger.info('%s(%d)님이 %s 앨범(%d)에 사진(%d)을 올렸습니다.' % (u.name, u.id, a.name, a.id, p.id))
        return redirect('yighub:photos', album_id = album_id)
    else:
        form = PhotoForm()

    logger.info('%s(%d)님이 %s 앨범(%d)에 사진 올리기 페이지를 열었습니다.' % (u.name, u.id, a.name, a.id))
    return render(request, 'yighub/create_photos.html', 
        {'user' : u, 'public_dict' : PublicBoardDict, 'album' : a, 'form' : form, })


def edit_photo(request, album_id, photo_id):
    pass
def delete_photo(request, album_id, photo_id):
    try:
        p = Photo.objects.get(pk = photo_id)
    except Photo.DoesNotExist:
        raise Http404

    # 권한 검사
    permission = check_permission(request, 'albums', p.album, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if u == p.photographer:
        
        # 게시판 정보를 업데이트한다.
        a = p.album
        if p.time_created == a.newest_time:
            if a.count_photo > 1: 
                prev_photo = a.photos.order_by('-time_created')[1]
                a.newest_time = prev_photo.time_created # 수정된 시간은 최신 시간에 반영하지 않는다.
            else: # 게시판에 글이 하나 남았을 때
                pass # a.newest_time = None # None이 되면 앨범 목록에서 맨 밑으로 내려간다.
        a.count_photo -= 1

        a.save()

        logger.info('%s(%d)님이 %s 앨범(%d)에서 사진(%d)을 삭제했습니다.' % (u.name, u.id, a.name, a.id, p.id))

        p.delete()
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )
        #return render(request, 'yighub/error.html', {'error' : 'invalid approach'})

    return redirect('yighub:photos', album_id=album_id)

def recommend_photo(request, album_id, photo_id):

    # 권한 검사
    permission = check_permission(request, 'albums', get_object_or_404(Album, pk=album_id), mode = 'writing')
    if permission[0] == False:
        return permission[1]

    try:
        p = Photo.objects.get(pk = photo_id) 
    except Photo.DoesNotExist:
        raise Http404

    u = User.objects.get(user_id = request.session['user_id'])
    if u in p.recommendation.all():
        messages.error(request, 'You already recommend this')
        return render(request, 'yighub/error.html', )
    p.recommendation.add(u)
    p.count_recommendation += 1
    p.save()

    logger.info('%s(%d)님이 사진(%d)을 추천했습니다.' % (u.name, u.id, p.id))
    return redirect('yighub:photos', album_id = album_id)

def delete_recommend_photo(request, album_id, photo_id):

    # 권한 검사
    permission = check_permission(request, 'albums', get_object_or_404(Album, pk=album_id), mode = 'writing')
    if permission[0] == False:
        return permission[1]
      
    try:
        p = Photo.objects.get(pk = photo_id) 
    except Photo.DoesNotExist:
        raise Http404

    u = User.objects.get(user_id = request.session['user_id'])
    if u in p.recommendation.all():
        p.count_recommendation -= 1
        p.recommendation.remove(u)
        p.save()

        logger.info('%s(%d)님이 사진(%d) 추천을 취소했습니다.' % (u.name, u.id, p.id))
        return redirect('yighub:photos', album_id = album_id)
    else:
        messages.error(request, 'You have not recommended this')
        return render(request, 'yighub/error.html', )


def comment_photo(request, album_id, photo_id):
    
    if request.method == 'POST':
        p = get_object_or_404(Photo, pk = photo_id)
        try:
            newest_comment = PhotoComment.objects.order_by('-arrangement')[0]
        except IndexError:
            arrangement = 0
        else:
            arrangement = (newest_comment.arrangement//1000 + 1) * 1000

        u = User.objects.get(user_id = request.session['user_id'])

        c = PhotoComment(photo = p,
                    content = request.POST['content'],
                    creator = u,
                    time_created = timezone.now(),
                    arrangement = arrangement,
                    )
        c.save()

        logger.info('%s(%d)님이 사진(%d)에 댓글을 달았습니다: "%s"(%d)' % (u.name, u.id, p.id, c.content, c.id))
        return redirect('yighub:photos', album_id = album_id) 
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def delete_comment_photo(request, album_id, photo_id, comment_id):
    
    try:
        p = Photo.objects.get(pk = photo_id)
        c = PhotoComment.objects.get(pk = comment_id)
    except (Photo.DoesNotExist, PhotoComment.DoesNotExist):
        raise Http404

    # 권한 검사
    permission = check_permission(request, 'albums', p.album, mode = 'writing')
    if permission[0] == False:
        return permission[1]

    u = User.objects.get(user_id = request.session['user_id'])

    if u == c.creator:

        logger.info('%s(%d)님이 사진(%d)에서 댓글을 삭제했습니다: "%s"(%d)' % (u.name, u.id, p.id, c.content, c.id))
        c.delete()
        return redirect('yighub:photos', album_id = album_id)

    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def reply_comment_photo(request, album_id, photo_id, comment_id):
    pass
def recommend_comment_photo(request, album_id, photo_id, comment_id):
    pass

def search(request, board_id, keyword, page):

    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':

        keyword = iri_to_uri(urlquote(request.POST['keyword'], safe='')) # iri_to_uri가 필요한지는 의문. urlquote_plus가 더 나을지도. urlquote_plus는 safe도 필요없음.

        try:
            b = Board.objects.get(pk = board_id)
        except:
            logger.info('%s(%d)님이 모든 게시물에서 "%s" 키워드로 검색했습니다.' % (u.name, u.id, request.POST['keyword']))
        else:
            logger.info('%s(%d)님이 %s 게시판에서 "%s" 키워드로 검색했습니다.' % (u.name, u.id, b.name, request.POST['keyword']))

        if keyword:
            return redirect('yighub:search', board_id=board_id, keyword=keyword, page=1)
        else:
            return redirect('yighub:home')

    keyword = unquote(keyword)
    # keywords = keyword.strip().split()
    result_entry = set()
    board_id = int(board_id)

    try: # 게시판 내 검색인지 검사
        b = Board.objects.get(pk = board_id)
    except:
        public_entrys = PublicEntry.objects.all()
        bulletin_entrys = BulletinEntry.objects.all()
        taskforce_entrys = TaskforceEntry.objects.all()
        b = None
    else:
        public_entrys = PublicEntry.objects.filter(board__id = b.id)
        bulletin_entrys = BulletinEntry.objects.filter(board__id = b.id)
        taskforce_entrys = TaskforceEntry.objects.filter(board__id = b.id)

    # for keyword in keywords:
    for e in public_entrys.filter(creator__name__contains = keyword):
        e.board_type = 'public'
        result_entry.add(e)
    for e in bulletin_entrys.filter(creator__name__contains = keyword):
        e.board_type = 'bulletin'
        result_entry.add(e)
    for e in taskforce_entrys.filter(creator__name__contains = keyword):
        e.board_type = 'taskforce'
        result_entry.add(e)

    for e in public_entrys.filter(title__contains = keyword):
        e.board_type = 'public'
        result_entry.add(e)
    for e in public_entrys.filter(content__contains = keyword):
        e.board_type = 'public'
        result_entry.add(e)
    for e in bulletin_entrys.filter(title__contains = keyword):
        e.board_type = 'bulletin'
        result_entry.add(e)
    for e in bulletin_entrys.filter(content__contains = keyword):
        e.board_type = 'bulletin'
        result_entry.add(e)
    for e in taskforce_entrys.filter(title__contains = keyword):
        e.board_type = 'taskforce'
        result_entry.add(e)
    for e in taskforce_entrys.filter(content__contains = keyword):
        e.board_type = 'taskforce'
        result_entry.add(e)

    current_page = int(page)
    page_size = 20
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    result_entry = list(result_entry)
    count_entry = len(result_entry)
    entry_list = sorted(result_entry, key = lambda r: r.time_created, reverse = True)[no : (no + page_size)] 

    bulletin_list = get_board_list('bulletin')
    taskforce_list = get_board_list('taskforce')

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)//page_size + 1

    # 페이지 리스트 만들기
    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 5
    next_page = current_page + 5

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 5:
        next_page = 0
        last_page = 0
    if current_page <= 5:
        prev_page = 0
        first_page = 0

    p = {'entry_list' : entry_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

    if b:
        logger.info('%s(%d)님이 %s 게시판 "%s" 키워드 검색 %s 페이지를 열었습니다.' % (u.name, u.id, b.name, keyword, page))
    else:
        logger.info('%s(%d)님이 모든 게시물 "%s" 키워드 검색 %s 페이지를 열었습니다.' % (u.name, u.id, keyword, page))


    return render(request, 'yighub/search.html',
        {'user': u, 'public_dict' : PublicBoardDict, 
        'bulletin_list' : bulletin_list, 
        'taskforce_list' : taskforce_list, 'page' : p, 
        'board_id' : board_id, 'keyword' : keyword, 
        'current_board' : b, 'count' : count_entry})

def search_albums(request, keyword, page):

    board = 'albums'

    # 권한 검사
    permission = check_permission(request, board, )
    if permission[0] == False:
        return permission[1]
    u = User.objects.get(user_id = request.session['user_id'])

    if request.method == 'POST':

        keyword = iri_to_uri(urlquote(request.POST['keyword'], safe='')) # iri_to_uri가 필요한지는 의문. urlquote_plus가 더 나을지도. urlquote_plus는 safe도 필요없음.

        logger.info('%s(%d)님이 앨범에서 "%s" 키워드로 검색했습니다.' % (u.name, u.id, request.POST['keyword']))

        if keyword:
            return redirect('yighub:search_albums', keyword=keyword, page=1)
        else:
            return redirect('yighub:home')

    keyword = unquote(keyword)
    # keywords = keyword.strip().split()
    results = set()

    # for keyword in keywords:
    for a in Album.objects.all():
        if keyword in a.name:
            results.add(a)
        if a.photos.filter(photographer__name__contains = keyword):
            results.add(a)
        if a.photos.filter(description__contains = keyword):
            results.add(a)
        
    page_size = 12
    current_page = int(page) if page != '0' else 1
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    count_album = len(results)
    album_list = sorted(list(results), key = lambda r: r.newest_time, reverse = True)[no : (no + page_size)] 

    albums = []
    for album in album_list:
        try:
            albums += [{'album':album, 'thumbnail':album.photos.all()[0]}]
        except:
            albums += [{'album':album, 'thumbnail':None}]

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_album - 1)//page_size + 1

    # 페이지 리스트 만들기
    if last_page <= 7:
        start_page = 1
    elif current_page <= 4:
        start_page = 1
    elif current_page > last_page - 4:
        start_page = last_page - 6        
    else:
        start_page = current_page - 3

    if last_page <= 7:
        end_page = last_page
    elif current_page > last_page - 4:
        end_page = last_page
    elif current_page < 4:
        end_page = 7
    else:
        end_page = current_page + 3

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 5
    next_page = current_page + 5

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page > last_page - 4:
        next_page = 0
        last_page = 0
    if current_page <= 4:
        prev_page = 0
        first_page = 0

    p = {'album_list' : album_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

    logger.info('%s(%d)님이 앨범에서 "%s" 키워드 검색 %s 페이지를 열었습니다.' % (u.name, u.id, keyword, page))
    return render(request, 'yighub/search_albums.html', {'user':u, 'public_dict' : PublicBoardDict, 'albums':albums, 'page':p, 'keyword':keyword})

def waiting(request):
    return render(request, 'yighub/waiting.html')

def error500(request):
    return render(request, 'yighub/500.html')
# not used anymore
# def man_won_bbang(request):

#     permission = check_permission(request, 'memo')
#     if permission[0] == False:
#         return permission[1] 
#     u = User.objects.get(user_id = request.session['user_id'])
    
#     bulletin_list = get_board_list('bulletin')
#     taskforce_list = get_board_list('taskforce')

#     betting_list, averages = betting_list_now()

#     logger.info('%s(%d)님이 만원빵 페이지를 열었습니다.' % (u.name, u.id))

#     return render(request, 'yighub/man_won_bbang.html',
#         {'user': u, 'public_dict' : PublicBoardDict, 
#         'bulletin_list' : bulletin_list, 
#         'taskforce_list' : taskforce_list, 
#         'betting_list' : betting_list,
#         'averages' : averages,
#         })

# def transform_user(request,):
#     transformation.transform_user()
#     return HttpResponse("Success!")

# def transform_data(request,):
#     transformation.transform_board('data', 'Bulletin')
#     transformation.transform_comment('data', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_column(request,):
#     transformation.transform_board('column', 'Bulletin')
#     transformation.transform_comment('column', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_portfolio(request,):
#     transformation.transform_board('portfolio', 'Bulletin')
#     transformation.transform_comment('portfolio', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_analysis(request,):
#     transformation.transform_board('analysis', 'Bulletin')
#     transformation.transform_comment('analysis', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_notice(request,):
#     transformation.transform_board('m_notice', 'Bulletin')
#     transformation.transform_comment('m_notice', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_board(request,):
#     transformation.transform_board('board', 'Bulletin')
#     transformation.transform_comment('board', 'Bulletin')
#     return HttpResponse("Success!")

# def transform_tf(request,):
#     transformation.transform_board('tf', 'Taskforce')
#     transformation.transform_comment('tf', 'Taskforce')
#     return HttpResponse("Success!")

# def transform_research(request,):
#     transformation.transform_board('Research', 'Public')
#     transformation.transform_comment('Research', 'Public')
#     return HttpResponse("Success!")

# def transform_fund(request,):
#     transformation.transform_board('fund', 'Public')
#     transformation.transform_comment('fund', 'Public')
#     return HttpResponse("Success!")

# def transform_photos(request,):
#     transformation.transform_photos()
#     return HttpResponse("Success!")

# def transform_memo(request,):
#     transformation.transform_memo()
#     return HttpResponse("Success!")


