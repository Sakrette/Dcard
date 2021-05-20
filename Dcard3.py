from time import sleep as _sleep
#import requests as _requests
import cloudscraper as _cloudscraper
import re as _re, os as _os
from datetime import datetime as _datetime
from pytz import timezone as _timezone
import pickle as _pickle, json as _json
from http.cookies import SimpleCookie as _SimpleCookie
import platform

# local modules
import Imgur as _Imgur


_fileopen = open
_now = _datetime.now

_postSignature = _replySignature = ""
_apiroot = "https://www.dcard.tw/service/api/v2/"


PyVer = ".".join(map(str, _os.sys.version_info[:3]))
Platform = f'{platform.system()} {_os.name.upper()} {platform.release()}'
UserAgent = {'User-Agent': f'Mozilla/5.0 ({Platform}; {_os.sys.platform.capitalize()})'}

scraper = _cloudscraper.create_scraper()
scraper.headers.update(UserAgent)
_session = scraper #.Session()

__path__ = _re.match(r".*[\\/]", __file__)[0]

def page(p):
    return _apiroot + p




# error messages

_ERR_LIB = {
    2003: "has_logged_in",
    2007: "token_expired"
}



# decorators, helpers
def _check_token_expired(session_func, *args, **kwargs):
    result = session_func(*args, **kwargs)
    
    j = result.json()
    if 'error' in j:
        if j['error'] == 2007:
            _refresh()
            result = session_func(*args, **kwargs)

    return result






''' -------------------- Settings -------------------- '''

def newSession(session=None):
    global _session
    if session is None:
        _session = _cloudscraper.create_scraper() #Dc Session()
        scraper.headers.update(UserAgent)
    else:
        _session = session


def loadUser(user, login=True):
    global _postSignature, _replySignature
    _account = _password = _postSignature = _replySignature = ""
    if not _os.access(__path__ + "user.ini", _os.F_OK):
        print("[Error] Cannot found user.ini")
        return
    
    with _fileopen(__path__ + "user.ini", "rb") as ini:
        getting = False
        
        while True:
            line = ini.readline()
            if not line:
                break
            
            line = _re.sub("\r?\n", "", line.decode("utf8"))
            if line.startswith(f"[{user}]"):
                getting = True
            elif getting is True:
                if line.startswith("imgurID="):
                    _Imgur.loadUser(line[8:])
                elif line.startswith("account="):
                    _account = line[8:]
                elif line.startswith("password="):
                    _password = line[9:]
                elif line.startswith("postsign="):
                    _postSignature  = line[9:]
                elif line.startswith("postsign+="):
                    _postSignature += "\n" + line[10:]
                elif line.startswith("replysign="):
                    _replySignature  = "\n" + line[10:]
                elif line.startswith("replysign+="):
                    _replySignature += "\n" + line[11:]
                if line.startswith("["):
                    break
    if _account == "" or _password == "":
        print(f"Load User Faild: {user}")
        return
    elif not login:
        print(f"Loaded User Data: {user}")
        return
    else:
        # read last token from __TOKENS__.txt
##        token = ""
##        if _os.access("__TOKENS__.txt", _os.R_OK):
##            with open("__TOKENS__.txt", "r") as f:
##                tokens = [line.split()[-1] for line in f.read().split("\n") if line]
##            if tokens:
##                token = tokens[-1]
##        if token:
##            print("[Notice] Read Token:", token)
##        else:
        _refresh(True)
        response = _session.post("https://www.dcard.tw/service/sessions", json={"email":_account, "password":_password})
        if response.status_code == 204:
            print("[Notice] Logged in successfully!")
            _save_data()
        else:
            print("[Error] Log in failed...")
            print(response.text)
        return response

# Token
def _refresh(get_token=False):
    if get_token:
        headers = _session.get("https://www.dcard.tw/service/_ping").headers
        #print(dir(_session))
        #print(headers)
        token = headers['X-CSRF-TOKEN']
        print("[Notice] New token:", token)
        #print(_now(), ":", token, file=_fileopen(__path__ + "__TOKENS__.txt", "a+"))
        _session.headers.update({"X-CSRF-TOKEN":token})

    resp = _session.post("https://www.dcard.tw/service/oauth/refresh")
    if 'Set-Cookie' in resp.headers:
        cookies = _SimpleCookie(resp.headers['Set-Cookie'].replace('httponly,', 'httponly;'))
        for c in cookies:
            cookies[c].update({'expires': _datetime.strptime(cookies[c]['expires'], '%a, %d %b %Y %H:%M:%S GMT').strftime('%a, %d-%b-%Y %H:%M:%S GMT')})
        _session.cookies.update(cookies)
        _save_data()

# Cookies
def _save_data(pkl_file="__cookies__.pkl"):
    # dump login data
    _dcard_cookies = _cloudscraper.requests.cookies.RequestsCookieJar()
    for cookie in _session.cookies:
        #if cookie.domain == ".dcard.tw":
            _dcard_cookies.set_cookie(cookie)
    _pickle.dump(_dcard_cookies, _fileopen(pkl_file, "wb"))
def _load_data(pkl_file="__cookies__.pkl"):
    _dcard_cookies = _pickle.load(_fileopen(pkl_file, "rb"))
    _session.cookies.update(_dcard_cookies)
    _refresh(True)
    

def setSignature(psign, rsign=None):
    global _postSignature, _replySignature
    _postSignature = "\n" + psign
    if rsign is not None:
        _replySignature = "\n" + rsign
    elif rsign is True:
        _replySignature = "\n" + psign



''' -------------------- Get Status -------------------- '''

def isLogin():
    me = _session.get(page("me"))
    return me.status_code == 200    




''' -------------------- Get Informations -------------------- '''

class Post:
    class Comment:
        def __init__(self, **kwargs):
            self.floor        = -1    # floor
            self.host         = False # is the host
            self.gender       = ""    # F/M/D
            self.withNickname = False # is with nickname
            self.school       = ""    # school or nickname
            self.department   = ""    # depart or nickname_id
            self.id           = ""    # comment id
            self.content      = ""    # content

            self.createdAt    = ""
            self.isSuspiciousAcount = False
            
            
            # reported comment
            self.hidden       = False
            self.reportReason = ""
            self.reportReasonText = ""

            # unknown            
            self.postAvatar   = ""

            for _ in kwargs:
                setattr(self, _, kwargs[_])
                
        def __str__(self):
            poster   = f"B{self.floor} {self.gender} {self.school} " + "@"[:self.withNickname] + + ('' if self.anonymousDepartment else self.department)
            posttime = _datetime.strptime(self.createdAt, "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(_timezone("Asia/Taipei")).strftime("%Y/%m/%d %H:%M:%S %Z%z")
            content  = self.content
            return poster + " " + posttime + "\n" + content

        def delete(self):
            dlcmt = _session.delete(page(f"comments/{self.id}"))
            return dlcmt
            
    def __init__(self, postid):
        # post info
        self.id           = -1    # post id
        self.title        = ""    # title
        self.replyId      = None  # reply id
        self.replyTitle   = None  # reply title
        self.forumId      = ""
        self.forumName    = ""
        self.forumAlias   = ""
        # host info
        self.gender         = ""    # F/M/D
        self.withNickname   = False # is with nickname
        self.school         = ""    # school or nickname
        self.anonyousSchool = False # anonymous school
        self.department     = ""    # depart or nickname_id
        self.content        = ""    # content
        self.topics         = []    # topics
        
        self.createdAt    = ""
        self.isSuspiciousAcount = False

        self.commentCount = -1    #
        self.reactions    = []
        
        # reported comment
        self.hidden       = False
        self.reportReason = ""
        self.reportReasonText = ""

        # unknown            
        self.postAvatar   = ""

        
        post_json = _check_token_expired(_session.get, page(f"posts/{postid}")).json()
        
        for _ in post_json:
            setattr(self, _, post_json[_])

    def __str__(self):
        title    = self.title
        poster   = f"{self.gender} {self.school} " + "@"[:self.withNickname] + + ('' if self.anonymousDepartment else self.department)
        posttime = _datetime.strptime(self.createdAt, "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(_timezone("Asia/Taipei")).strftime("%Y/%m/%d %H:%M:%S %Z%z")
        content  = self.content
        return "\n".join([title, poster + " " + posttime, content])

    # reaction
    def react(self, reaction=None):
        reactions = {
            'like': {
                'id': '286f599c-f86a-4932-82f0-f5a06f1eca03',
                'aliases': ['heart']
            },
            'laugh': {
                'id': 'e8e6bc5d-41b0-4129-b134-97507523d7ff',
                'aliases': ['haha']
            },
            'shock': {
                'id': '4b018f48-e184-445f-adf1-fc8e04ba09b9',
                'aliases': ['wow', 'surprise']
            },
            'kneel': {
                'id': '011ead16-9b83-4729-9fde-c588920c6c2d',
                'aliases': []
            },
            'sorry': {
                'id': '514c2569-fd53-4d9d-a415-bf0f88e7329f',
                'aliases': ['sad']
            },
            'angry': {
                'id': 'aa0d425f-d530-4478-9a77-fe3aedc79eea',
                'aliases': ['mad']
            }
        }

        resp = None
        if reaction is None:
            resp = _check_token_expired(_session.delete, page(f'posts/{self.id}/reactions'))
        else:
            if reaction in reactions:
                resp =  _check_token_expired(_session.post, page(f'posts/{self.id}/reactions'), data={'reactionId': reactions[reaction]['id']})
            else:
                for react in reactions:
                    if reaction in reactions[react]['aliases']:
                        resp = _check_token_expired(_session.post, page(f'posts/{self.id}/reactions'), data={'reactionId': reactions[react]['id']})
                        break
                else:
                    print('[Error] Invalid reaction:', reaction)
                    return
        return resp.content
        
    #reply
    def reply   (self, content1, *contents):
        return reply   (self.id, content1, *contents)
    def replyImg(self, content1, *contents):
        return replyImg(self.id, content1, *contents)

    #cross, post-reply
    def postreply   (self, title, content1, *contents, topics=(), forum=None,  anonymous=False):
        if forum is None:
            forum = self.forumAlias
        return post   (forum, title, content1, *contents, topics=(), reply=self,  anonymous=False)
    def postreplyImg(self, title, content1, *contents, topics=(), forum=None,  anonymous=False):
        if forum is None:
            forum = self.forumAlias
        return postImg(forum, title, content1, *contents, topics=(), reply=self,  anonymous=False)
    

    # post comments
    def refresh(self):
        post_id = self.id
        self.__init__(self.id)
        if self.commentCount == -1:
            _refresh()
            self.__init__(post_id)
        print("Comments:", self.commentCount)
    def comment(self, floor):
        floors = self.commentCount
        if floor>floors:
            return
        elif floor>0:
            return Post.Comment(**_check_token_expired(_session.get, page(f"posts/{self.id}/comments?after={floor-1}")).json()[0])
        elif 0>floor>=-floors:
            return Post.Comment(**_check_token_expired(_session.get, page(f"posts/{self.id}/comments?after={floors-floor}")).json()[0])
        else:
            return
    @property
    def comments(self):
        uplimit = 100 # may be changed
        for after in range(0, self.commentCount+uplimit, uplimit):
            for comment in map(lambda kw:Post.Comment(**kw), _check_token_expired(_session.get, page(f"posts/{self.id}/comments?after={after}&limit={uplimit}")).json()):
                yield comment
        #return cmts

    @property
    def links(self):
        return _check_token_expired(_session.get, page(f'posts/{self.id}/links'))

    # post operations
    def delete(self):
        dlpost = _check_token_expired(_session.delete, page(f"posts/{self.id}"))
        return dlpost

    def export(self, filename=None, directory=".", logmode="B"):
        if filename is None:
            filename = f"Post-{self.id}.txt"
        else:
            filename = str(filename)
        
        if not _os.access(directory, _os.F_OK):
            dirs = directory.replace("\\", "/").split("/")
            for i in range(len(dirs)):
                d = "/".join(dirs[:i+1])
                if not _os.access(d, _os.F_OK):
                    _os.mkdir(d)
                    print(f"Created folder: {d}")
                elif _os.path.isfile(d):
                    print(f"Cannot create folder: {d}")
                    return
        
        # temporarily use fixed format
        filesize = 0
        with open(f"{directory}/{filename}", "wb+") as file:
            filesize += file.write(str(self).encode("utf8"))
            filesize += file.write(b"\n\n")
            print("Exported: Post")
            for comment in self.comments:
                filesize += file.write(str(comment).encode("utf8"))
                filesize += file.write(b"\n\n")
                if logmode=="B":
                    print(f"Exported B{comment.floor}")
                elif logmode=="/":
                    print(f"Exported {comment.floor}/{self.commentCount}")
                elif logmode=="%":
                    if (comment.floor-1)/self.commentCount*100//1 != comment.floor/self.commentCount*100//1:
                        print(f"Exported {comment.floor/self.commentCount*100//1}%")
        print(f"Export Completed: {filename} ({filesize} bytes)")
    
def posts(forum="", popular=False, limit=30, before=0):
    max_limit = 100
    
    posts_json = []
    while limit > max_limit:
        posts_json += _check_token_expired(_session.get, page((forum and ("forums/" + forum + "/"))
                                   +f"posts?popular={str(popular).lower()}&limit={max_limit}"
                                   + [f"&before={before}", ""][before<1])).json()
        before = posts_json[-1]['id']
        limit -= max_limit
    else:
        posts_json += _check_token_expired(_session.get, page((forum and ("forums/" + forum + "/"))
                                   +f"posts?popular={str(popular).lower()}&limit={limit}"
                                   + [f"&before={before}", ""][before<1])).json()
        
    class PostOverlook:
        def __init__(self, json):
            for _ in json:
                setattr(self, _, json[_])
        def __repr__(self):
            title    = self.title
            poster   = f"{self.gender} {self.school} " + "@"[:self.withNickname] + ('' if self.anonymousDepartment else self.department)
            posttime = _datetime.strptime(self.createdAt, "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(_timezone("Asia/Taipei")).strftime("%Y/%m/%d %H:%M:%S %Z%z")
            content  = self.excerpt
            return "\n".join([title, poster + " " + posttime, content])
    
    return [*map(PostOverlook, posts_json)]


class me:
    @property
    def info(self):
        if 'dg-authorization' in _session.headers:
            del _session.headers['dg-authorization']
            _refresh()
        resp_me = _session.get(page('me'))
        return resp_me.json()

    @classmethod
    def posts(password, before=-1):
        _refresh()
        resp_sudo = _session.post("https://www.dcard.tw/service/oauth/sudo", json=({"password": password, "grant_type":"refresh_token"}))
        if resp_sudo.status_code != 200:
            print(resp_sudo)
            return resp_sudo
        token = json.loads(resp_sudo.text)['accessToken']
        _session.headers.update({'dg-authorization': f"Bearer {token}"})
        resp_posts = _session.get(page("me/posts" + ("" if before==-1 else f"?before={before}")))
        posts = json.loads(resp_posts.text)
        return posts


''' -------------------- Post/Reply -------------------- '''

def post(forum, title, content1, *contents, topics=(), reply="", anonymous=False):
    suburl = "posts"
    data = dict()

    #forum
    suburl = f"forums/{forum}/{suburl}"
    
    #anonymous
    data.update({"anonymous":str(anonymous).lower()})

    #title
    data.update({"title":title})
    
    #reply post
    if type(reply) is Post:
        reply = reply.id
    if reply:
        suburl = f"posts/{reply}/cross"
        data.update({"to":forum})
    
    #content
    content = "\n".join([content1, *contents, _postSignature])
    postlimit = 30000
    if len(content)>postlimit:
        content = content[:-1-len(_postSignature)]
        content_more = "(Continue B0 ...)\n\n" + content[postlimit-1-len(_postSignature):]
        content = content[:postlimit-1-len(_postSignature)] + "\n" + _postSignature
    else:
        content_more = ""
    data.update({"content":content})

    #topics    
    data.update({"topics":topics})

    for _ in range(12):
        try:
            p = _check_token_expired(_session.post, page(suburl), data=data).json()['id']
            postid = Post(p)
            break
        except:
            if _<11:
                print(f"Failed posting [{_+1}], trying in 5 seconds...")
                _sleep(5)
                continue
    else:
        raise Exception('[Error] Post Failed')
        
    if content_more:
        reply(postid, content_more)
    print(f"[Succeed] Posted: {title} - https://www.dcard.tw/f/{forum}/p/{postid.id}")
    return postid

        
def postImg(forum, title, content1, *contents, topics=(), reply="", anonymous=False):
    '''suburl = "posts"
    data = dict()

    #forum
    suburl = f"forums/{forum}/{suburl}"
    
    #anonymous
    data.update({"anonymous":str(anonymous).lower()})

    #title
    data.update({"title":title})
    
    #reply post
    if type(reply) is Post:
        reply = reply.id
    #unknown yet
    #data.update({"":reply})
    '''
    #content
    content = ""
    for c in [content1, *contents]:
        if c.startswith("i:"):
            # post image from url
            imgurl = _Imgur.upload(c[2:], filetype="file")
            if imgurl is not None:
                content += imgurl.link
            else:
                content += "[Failed to upload the image to Imgur]"
        else:
            if c.startswith("t:"):
                c = c[2:]
            content += c
        content += "\n"
##    content += _postSignature
    
    return post(forum, title, content, topics=topics, reply=reply, anonymous=anonymous)
    '''
    if len(content)>30000:
        content_more = content[30000:]
        content = content[:30000]
    else:
        content_more = ""
    
    data.update({"content":content})

    #topics    
    data.update({"topics":topics})

    for _ in range(12):
        try:
            postid = Post(_session.post(page(suburl), data=data).json()['id'])
            break
        except:
            if _<11:
                print(f"Failed posting [{_+1}], trying in 5 seconds...")
                _sleep(5)
                continue
        if content_more:
            reply(postid, content_more)
        return postid
    else:
        print("[Error] Post Failed")
    '''


def reply(postid, content1, *contents):
    suburl = f"posts/{postid}/comments"

    content = "\n".join([content1, *contents])
    
    if len(content) > 10000:
        content_more = content[10000:]
        content = content[:10000]
    else:
        content_more = ""
    # need modify
    content += "\n" + _replySignature

    for t in range(10):
        try:
            cmt = Post.Comment(**_check_token_expired(_session.post, page(suburl), data={"content":content}).json())
            break
        except:
            print(f"[Error] Failed to reply, retrying... ({t+1})")
            _sleep(1)
    else:
        # failed for 10 times
        raise Exception("[Notice] Failed to reply.")
##        return Post.Comment() # empty comment object
    p = Post(postid)
    
    if content_more:
        content_more = f"(Continue B{cmt.floor} ...)\n\n" + content_more
        reply(postid, content_more)
    print(f"[Succeed] Replied: {p.title} - https://www.dcard.tw/f/{p.forumAlias}/p/{postid}?floor={cmt.floor}")
    return cmt
        


    
def replyImg(postid, content1, *contents):
    #suburl = f"posts/{postid}/comments"

    content = ""
    for c in [content1, *contents]:
        if c.startswith("i:"):
            # post image from url
            imgurl = _Imgur.upload(c[2:], filetype="file")
            if imgurl is not None:
                content += imgurl.link
            else:
                content += "[Failed to upload the image to Imgur]"
        else:
            if c.startswith("t:"):
                c = c[2:]
            content += c
        content += "\n"
    
    return reply(postid, content[:-1])
    
    '''
    if len(content) > 11000:
        content_more = content[11000:]
        content = content[:11000]
    else:
        content_more = ""
    
    cmt = Post.Comment(**_session.post(page(suburl), data={"content":content}).json())
    
    if content_more:
        content_more = f"(Continue B{cmt.floor} ...)\n\n" + content_more
        reply(postid, content_more)
        
    return cmt
    '''
    

def export(post, filename=None, directory=".", logmode="B"):
    p = Post(post)
    if p.id == -1:
        print(f"Cannot find post: {post}")
        return
    
    filesize = p.export(filename, directory, logmode)
    return filesize
