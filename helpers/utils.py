# -*- coding: utf-8 -*-

import web
from web import http

#import pycurl, random, re, cStringIO, types, urllib
import random, re, cStringIO, types, urllib
import urlparse as _urlparse

#from lxml import etree
#from md5 import md5
import os
import hashlib
from datetime import datetime, date, timedelta
from decimal import Decimal
import time
import json
import traceback

from helpers.pinyin import PinYin
pinyin = PinYin()
try:
    pinyin.load_word()
except:
    traceback.print_exc()

class DateTimeJSONEncoder(json.JSONEncoder):
    """json模块不能直接编码日期时间类型，扩展JSONEncoder类处理日期时间类型，使用时dumps('',cls=DateTimeJSONEncoder)"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, Decimal):
            return "%.2f" % obj
        elif isinstance(obj, timedelta): # 对应mysql的time字段类型
            s = str(obj) # [H]H:MM:SS
            if len(s)==7:
                s = '0'+s
            return s
        else:
            try:
                return json.JSONEncoder.default(self, obj)
            except:
                return str(obj)

def url_encode(url):
    return http.urlencode(url)

def url_unquote(url):
    return urllib.unquote_plus(url)

def url_parse(url):
    return web.storage(
        zip(('scheme', 'netloc', 'path', 'params', 'query', 'fragment'), _urlparse.urlparse(url)))

def url_join(url, url_relative):
    if '://' not in url_relative:
        if not url_relative.startswith('/'):
            url_relative = '/' + url_relative
    return _urlparse.urljoin(url, url_relative)

def url_append_params(url, params):
    p = ('&' if url.find('?')>0 else '?')
    for k,v in params.items():
        url += '%s%s=%s'%(p,k,v)
    return url

def get_user_ip():
    return web.ctx.get('ip', '000.000.000.000')

#def parse_xml(txt):
#    xml = re.sub('xmlns\s*=\s*["\'].*?["\']', ' ', txt) # we remove the xmlns for simplicity
#    return etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False))

#def curl_init():
#    curl = pycurl.Curl()
#    curl.setopt(pycurl.USERAGENT, "Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)")
#    curl.setopt(pycurl.FOLLOWLOCATION, True)
    #curl.setopt(pycurl.CONNECTTIMEOUT, 3)
    #curl.setopt(pycurl.TIMEOUT, 30)

    return curl

# PIL complains when only f is returned but all we are doing is stringIO(f.getvalue()) twice.
#def open_url(curl, url, referer=None):
#    curl.setopt(pycurl.URL, url)
#    if referer:
#        curl.setopt(pycurl.REFERER, referer)

#    f = cStringIO.StringIO()
#    curl.setopt(pycurl.WRITEFUNCTION, f.write)
#    curl.perform()

#    html = f.getvalue()
#    f.close()

#    return html

def dnl(url, referer = None):
    c = curl_init()
    f = open_url(c, url, referer)
    c.close()
    return f

def dict_remove(d, *keys):
    for k in keys:
        if d.has_key(k):
            del d[k]

def get_extension_from_url(url):
    path = url_parse(url).path
    return path[path.rindex('.')+1:]

def get_unique_md5():
    return md5(str(datetime.now().microsecond)).hexdigest()

def get_guid():
    guid = get_unique_md5().upper()
    return '%s-%s-%s-%s-%s' % (guid[0:8], guid[8:12], guid[12:16], guid[16:20], guid[20:32])

def get_file_md5(filename):
    import os, hashlib
    if os.path.isfile(filename):
        fle = open(filename, 'rb')
        data = fle.read()
        fle.close()
        return hashlib.md5(data).hexdigest()
    else:
        return ''

def get_all_functions(module):
    functions = {}
    for f in [module.__dict__.get(a) for a in dir(module) if isinstance(module.__dict__.get(a), types.FunctionType)]:
        functions[f.__name__] = f
    return functions

def get_this_functions(module,funname):
    functions = {}
    for f in [module.__dict__.get(a) for a in dir(module) if isinstance(module.__dict__.get(a), types.FunctionType)]:
        if funname==f.__name__:
            functions[f.__name__] = f
    return functions

def email_errors():
    if web.config.email_errors:
        web.emailerrors(web.config.email_errors, djangoerror())

def is_blacklisted(text, blacklist):
    text = text.strip().lower()
    for banned_word in blacklist:
        banned_word = banned_word.decode('utf-8').strip()
        if banned_word.lower() in text:
            return banned_word
    return False

def get_jQueryDatatablesJSON(data,iTotalDisplayRecords=None,iTotalRecords=None,sEcho='1',oTotalSums=None):
    """将通过webpy.db返回的结果集list转换为JQuery Datatables需要的数据源格式（Ajax），主要是将list放在aaData中附加其他域返回dict"""
    data = data or []
    size = len(data)
    for x in data:
        if isinstance(x, dict):
            x.pop('ENCRYPT_PASSWORD','')
    iTotalRecords = iTotalRecords or size
    iTotalDisplayRecords = iTotalDisplayRecords or size
    oTotalSums = oTotalSums or {}
    retval = {"sEcho":sEcho,"iTotalRecords":iTotalRecords,"iTotalDisplayRecords":iTotalDisplayRecords,"aaData":data,"oTotalSums":oTotalSums}
    from config import formatting
    return formatting.json_string(retval)

def get_datetimestr(time=None, dbtype='mysql'):
    """得到指定时间的yyyy-mm-dd hh:mm:ss形式字符串，为数据库使用；Oracle时字符串不会自动转日期时间需要添加to_date函数"""
    time = time or datetime.now()
    retval = time.strftime('%Y-%m-%d %H:%M:%S')
    if dbtype=='oracle':
        retval = web.SQLLiteral("to_date('%s','yyyy-mm-dd hh24:mi:ss')"%retval)
    return retval

def get_currdatetimestr(dbtype='mysql'):
    """得到当前时间的yyyy-mm-dd hh:mm:ss形式字符串，为数据库使用；Oracle时字符串不会自动转日期时间需要添加to_date函数"""
    return get_datetimestr(None, dbtype)

def is_valid_date(text):
    '''判断是否是一个有效的日期字符串 yyyy-mm-dd'''
    try:
        return time.strptime(str(text), "%Y-%m-%d")
    except:
        return False

def is_valid_date2(text):
    '''判断是否是一个有效的日期字符串 yyyymmdd'''
    try:
        return time.strptime(str(text), "%Y%m%d")
    except:
        return False

def get_yyyymmdd(dt=None):
    """返回yyyymmdd形式整型日期值"""
    dt = dt or datetime.now()
    return dt.year*10000+dt.month*100+dt.day

def get_yyyy_mm_dd(val):
    """从yyyymmdd形式日期得到yyyy-mm-dd形式"""
    try:
        val = str(val)
        time.strptime(val, "%Y%m%d")
        syear = val[0:4]
        smonth = val[4:6]
        sday = val[6:8]
        return syear+'-'+smonth+'-'+sday
    except Exception, e:
        return val

def get_yyyymmddFromString(text):
    """从yyyy-mm-dd或yyyymmdd形式的字符中得到yyyymmdd形式的整型值或None值"""
    retval = is_valid_date(text) or is_valid_date2(text)
    if retval:
        return retval.tm_year*10000+retval.tm_mon*100+retval.tm_mday
    else:
        return None

def get_yyyymmddhhmmssFromString(text):
    """从yyyy-mm-dd hh:mm:ss形式的字符中得到yyyymmddhhmmss形式的整型值或None值"""
    try:
        retval = time.strptime(text, "%Y-%m-%d %H:%M:%S")
        if retval:
            return retval.tm_year*10000000000+retval.tm_mon*100000000+retval.tm_mday*1000000+retval.tm_hour*10000+retval.tm_min*100+retval.tm_sec
        else:
            return None
    except:
        return None

def get_yyyymmddhhmmFromString(text):
    """从yyyy-mm-dd hh:mm形式的字符中得到yyyymmddhhmm形式的整型值或None值"""
    try:
        retval = time.strptime(text, "%Y-%m-%d %H:%M")
        if retval:
            return retval.tm_year*10000000000+retval.tm_mon*100000000+retval.tm_mday*1000000+retval.tm_hour*10000+retval.tm_min*100
        else:
            return None
    except:
        return None

def validateEmail(email):
    if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email):
        return 1
    return 0

def debug(*args):
    print '='*50,args

def send_mail(receivers,sender,subject,content):
    import smtplib
    from email.mime.text import MIMEText
    mailto_list  = receivers
    mail_host    = sender.get('smtp') or 'smtp.qq.com' #设置服务器
    mail_user    = sender.get('user') or 'enfo@enfo.com.cn' #用户名
    mail_pass    = sender.get('pass') or 'X-87703605' #口令
    mail_postfix = sender.get('host') or 'enfo.com.cn' #发件箱的后缀

    if mail_user.find('@')>0:
        me = u"<"+mail_user+">"
    else:
        me = u"<"+mail_user+"@"+mail_postfix+">"   #这里的hello可以任意设置，收到信后，将按照设置显示
    msg = MIMEText(content,_subtype='html',_charset='utf8')    #创建一个实例，这里设置为html格式邮件
    msg['Subject'] = subject    #设置主题
    msg['From'] = me
    msg['To'] = ";".join(mailto_list)
    try:
        #连接smtp服务器，明文/SSL/TLS三种方式，根据你使用的SMTP支持情况选择一种
        #普通方式，通信过程不加密
        # smtp = smtplib.SMTP(mail_host)
        # smtp.ehlo()
        # smtp.login(mail_user,mail_pass)  #登陆服务器

        #tls加密方式，通信过程加密，邮件数据安全，使用正常的smtp端口
        smtp = smtplib.SMTP(mail_host)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(mail_user,mail_pass)  #登陆服务器

        #纯粹的ssl加密方式，通信过程加密，邮件数据安全
        # smtp = smtplib.SMTP_SSL(mail_host)
        # smtp.ehlo()
        # smtp.login(mail_user,mail_pass)  #登陆服务器

        #发送邮件
        smtp.sendmail(me, mailto_list, msg.as_string())  #发送邮件
        smtp.close()
        #注：目前虽然发送不会失败，但可能由于程序发送的邮件结构上不符合正规格式，并不能保证一定会收到，有些收邮件服务器会将其拦截
    except Exception, e:
        debug(None,str(e))
        return str(e)

def get_where_clause(keywords,cols,query=''):
    """
    返回SQL语句的where部分
        输入：查询关键字（多关键字使用空格分隔and关系）、参与过滤的字段名列表、附加条件语句
        输出：SQL语句的where部分
    """
    keywords = set(keywords.split())
    if not keywords or not cols:
        text_query = '(1=1)'
    else:
        def sqlands(col, keywords):
            return ' and '.join([col+' like '+kw for kw in keywords])
        #q = [str(web.sqlquote('%%' + w + '%%')) for w in keywords] #webpy处理中文unicode为\x形式会造成查询无法匹配
        q = ["'%"+w.replace("'","''")+"%'" for w in keywords]
        where = [sqlands(c,q) for c in cols]
        text_query = ' or '.join(where)
    if query:
        return "(("+text_query+") and ("+query+"))"
    else:
        return text_query

def get_where_clause2(keywords,cols,query=''):
    """
    返回SQL语句的where部分
        输入：查询关键字（多关键字使用空格分隔or关系）、参与过滤的字段名列表、附加条件语句
        输出：SQL语句的where部分
    """
    keywords = set(keywords.split())
    if not keywords or not cols:
        text_query = '(1=1)'
    else:
        def sqlors(col, keywords):
            return ' or '.join([col+' like '+kw for kw in keywords])
        #q = [str(web.sqlquote('%%' + w + '%%')) for w in keywords] #webpy处理中文unicode为\x形式会造成查询无法匹配
        q = ["'%"+w.replace("'","''")+"%'" for w in keywords]
        where = [sqlors(c,q) for c in cols]
        text_query = ' or '.join(where)
    if query:
        return "(("+text_query+") and ("+query+"))"
    else:
        return text_query

def get_where_clause3(keywords,cols,query=''):
    """
    返回SQL语句的where部分
        输入：查询关键字（多关键字使用空格分隔and关系）、参与过滤的字段名列表、附加条件语句
        输出：SQL语句的where部分
    """
    keywords = set(keywords.split())
    if not keywords or not cols:
        text_query = '(1=1)'
    else:
        def sqlors(cols, kw):
            return '(' + ' or '.join([col+' like '+kw for col in cols]) + ')'
        q = ["'%"+w.replace("'","''")+"%'" for w in keywords]
        where = [sqlors(cols,kw) for kw in q]
        text_query = ' and '.join(where)
    if query:
        return "(("+text_query+") and ("+query+"))"
    else:
        return text_query

def get_keyword():
    """得到一个基于时间戳的uuid并替换首位数字为字母并去掉中间的-号的字符串"""
    import uuid
    uusd = str(uuid.uuid1())
    if uusd[0] in '0123456789':
        uusd = chr(ord(uusd[0])+63)+uusd[1:]
    return uusd.replace('-','')
def replace_firstletter(uusd):
    """输入字符串首字母是0-9时替换成字母"""
    if uusd[0] in '0123456789':
        uusd = chr(ord(uusd[0])+63)+uusd[1:]
    return uusd.replace('-','')
def saveListToExcel(m,filename,titles=None):
    """保存list形式的数据集到Excel文件。输入：m为list类型数据集；titles为字段标题列表，每个元素为(key,value)，如果为空输出全部字段，否则输出key指定的字段，value为字段标题；filename为保存文件名"""
    if titles is None:
        titles = []
    try:
        import xlwt
        #样式
        fontNormal = xlwt.Font()
        fontNormal.name = 'Times New Roman'
        styleNormal = xlwt.XFStyle()
        styleNormal.font = fontNormal
        borders = xlwt.Borders()
        borders.left = 1
        borders.top = 1
        borders.right = 1
        borders.bottom = 1
        styleNormal.borders = borders
        #创建Excel文件对象并添加Sheet
        wb = xlwt.Workbook()
        ws0 = wb.add_sheet(filename) # set sheet name to filename
        #先生成标题行
        if not titles and m:
            titles = [(x,x) for x in m[0]]
        for i,(name,title) in enumerate(titles):
            ws0.write(0, i, title, styleNormal)
        #循环写数据
        for i,row in enumerate(m, 1):
            for j, (name,title) in enumerate(titles):
                # web.debug('%s: %r'%(name,row.get(name)))
                value = row.get(name) or u''
                if isinstance(value, str):
                    value = unicode(value)
                elif isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, timedelta): # 对应mysql的time字段类型
                    value = str(value) # [H]H:MM:SS
                    if len(value) == 7:
                        value = '0'+value
                elif isinstance(value, Decimal):
                    value = str(value)
                ws0.write(i, j, value, styleNormal)
        from config import app_root,os
        file_path = os.path.join(app_root, 'static', '%s.xls'%filename)
        wb.save(file_path)
        return file_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        # return traceback.format_exc()
        raise e

def formatFileSize(fsize):
    '''格式化文件大小'''
    if not str(fsize).isdigit():
        fsize = 0
    if fsize < 1024:
        return str(fsize)+'B'
    elif fsize < 1024*1024:
        return '%.2fKB' % (float(fsize)/1024)
    elif fsize < 1024*1024*1024:
        return '%.2fMB' % (float(fsize)/1024/1024)
    else:
        return '%.2fGB' % (float(fsize)/1024/1024/1024)

def getFileName(pathname):
    '''取带路径文件名的文件名'''
    sep = '/' if '/' in pathname else '\\'
    idx = pathname.rfind(sep)
    return pathname[idx+1:]

def getFileExtName(pathname):
    '''
        取带路径文件名的扩展名:
            getFileExtName('c:\\prog\\abc.py') -> 'py'
    '''
    fname = getFileName(pathname)
    idx = fname.rfind('.')
    if idx >= 0:
        return fname[idx+1:]
    else:
        return ''

def escapeLdapQuery(s):
    '''
        转义用作ldap查询里的字符串值的s，如：
        >>> s = 'K&R C'
        >>> escaped = escapeLdapQuery(s)
        >>> escaped
        'K\\26R C'
        >>> ldapFilter = '(book=%s)' % escaped
        >>> ldapFilter
        '(book=K\\26R C)'
    '''
    return ''.join( (('\\%02x'%ord(c) if c in ',;()&|=!><~*/\\' else c) for c in s) )

def loadInifile(filename):
    '''加载ini文件中的配置内容为dict格式'''
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(filename)
    retval = {}
    for x in config.sections():
        retval[x] = dict(config.items(x))
    return retval

def resizeImage(imgdata,w,h):
    '''利用PIL修改图片大小。输入：imgdata为文件数据。w,h其中之一可为0，若都为0就不修改图片大小直接返回。resize功能需要系统中安装有libjpeg-dev库'''
    if w==0 and h==0:
        return imgdata
    import Image
    from cStringIO import StringIO
    img = Image.open(StringIO(imgdata))
    p_w = int(w) if w.isdigit() else 0
    p_h = int(h) if h.isdigit() else 0
    if p_h!=0:
        p_w = img.size[0] * (img.size[1]/p_h)
    elif p_w!=0:
        p_h = img.size[1] * (img.size[0]/p_w)
    target = img.resize((p_w,p_h), Image.ANTIALIAS)  # 用PIL修改图片大小。参数呐！高保真必备！
    retval = StringIO()
    target.save(retf, "png")
    return retval

def floatget(f, default=None):
    ''' 转换为float '''
    try:
        return float(f)
    except (TypeError, ValueError):
        return default

def get_id_bytime(times=100):
    """根据时间戳返回一个整型id，输入times为倍数，乘以0.x秒"""
    import time
    time.sleep(0.01)
    retval = long((time.time()-1480000000)*times)
    return retval

def get_yyyymm():
    '''获取yyyymm格式的字符串'''
    return datetime.now().strftime('%Y%m')

def make_today_folder(parent):
    '''在指定目录下创建今天的目录。例如：输入 static，创建：static/2017/03/22。返回创建好的相对路径：static/2017/03/22'''
    yyyy = datetime.now().strftime('%Y')
    folder = os.path.join(parent,yyyy)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    mm = datetime.now().strftime('%m')
    folder = os.path.join(parent,yyyy,mm)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    dd = datetime.now().strftime('%d')
    folder = os.path.join(parent,yyyy,mm,dd)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    return folder

def timestamp2datetime(value):
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))

def get_time18():
    '''获取mmddhhnnss____格式的18位长度的字符串'''
    return datetime.now().strftime('%Y%m%d%H%M%S%f')[2:17] + str(random.random())[2:5]

def get_random_bytime():
    '''生成基于时间戳+随机数的随机数。yyyymmddhhnnss______****'''
    return datetime.now().strftime('%Y%m%d%H%M%S%f') + str(random.random())[2:6]

def get_random_number(length=6):
    '''得到指定长度的随机数字'''
    import time
    retval = str(int(time.time()*1000000)%1000000)
    while len(retval)<length:
        retval = '0'+retval
    return retval

def calc_pastseconds(rval):
    '''计算带时间的随机数过去的秒数'''
    # rval = '170301171822879362Pz0E3J'
    try:
        d = datetime.strptime(rval[:12], "%y%m%d%H%M%S")
        retval = (datetime.now() - d).seconds
    except Exception, e:
        retval = 0
    return retval

def get_random_string(length=6):
    '''得到一个指定长度的随机字符串'''
    stc = '0123456789abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    rang = len(stc)
    retval = ''
    for x in xrange(0,length):
        retval += stc[random.randint(0,rang)%rang]
    return retval

def ten_to_sixtwodecimal(value):
    '''10进制转62进制'''
    stc = '0123456789abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    length = len(stc)
    retval = ''
    intp = value / length
    remp = value % length
    while intp>0:
        retval = stc[remp]+retval
        remp = intp % length
        intp = intp / length
    retval = stc[remp]+retval
    return retval

def sixtwodecimal_to_ten(value):
    '''62进制转10进制'''
    stc = '0123456789abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    length = len(stc)
    retval = 0
    for x in xrange(len(value)):
        retval = retval+stc.find(value[x])*length**(len(value)-x-1)
    return retval

def ten_to_five(value):
    '''10进制转5进制'''
    stc = '01234'
    length = len(stc)
    retval = ''
    intp = value / length
    remp = value % length
    while intp>0:
        retval = stc[remp]+retval
        remp = intp % length
        intp = intp / length
    retval = stc[remp]+retval
    return retval
def five_to_ten(value):
    '''5进制转10进制'''
    stc = '01234'
    length = len(stc)
    retval = 0
    for x in xrange(len(value)):
        retval = retval+stc.find(value[x])*length**(len(value)-x-1)
    return retval

def sendGetRequest(url):
    """得到HTTP的GET请求返回内容"""
    import urllib2
    try:
        request = urllib2.Request(url)
        response = urllib2.urlopen(request).read()
    except urllib2.HTTPError,e:
        retval = e.info().get('enfo_error')
        return retval or e
    except urllib2.URLError,e:
        if hasattr(e,"reason"):
            return e.reason
        else:
            return e
    except Exception, e:
        return traceback.format_exc()
    else:
        return response

def sendPostRequest(url,data):
    """得到HTTP的POST请求返回内容"""
    import urllib2,urllib
    data = json.dumps(data)
    try:
        response = urllib2.urlopen(url, data)
        response = response.read()
    except urllib2.HTTPError,e:
        traceback.print_exc()
        retval = e.info().get('enfo_error')
        return retval or str(e)
    except urllib2.URLError,e:
        traceback.print_exc()
        if hasattr(e,"reason"):
            return e.reason
        else:
            return str(e)
    except Exception, e:
        traceback.print_exc()
        return traceback.format_exc()
    else:
        return response

def is_not_dummy_script(script):
    '''判断script不是无影响或作用的py脚本'''
    def is_dummy_script(script):
        if not script:
            return True
        for line in script.splitlines():
            line = line.lstrip()
            if line and line[0] != '#':
                return False
        return True
    return not is_dummy_script(script)

def check_required(param={},required=[]):
    '''检查输入参数param(dict)是否包含全部必要项required(list)。返回缺少的输入参数项'''
    required = set(required)
    inparams = set(param.keys())
    ret1 = list(required - inparams)
    if ret1: return ret1
    for k in required:
        if not param.get(k):
            return [k,]

# def sqlsafe(val):
#     '''
#         >>> [sqlsafe(x) for x in (None,'',u'中文','abc','"\'',0,-6,70000000000000L,Decimal('888.92'))]
#         ['null', "''", u"'\u4e2d\u6587'", "'abc'", '\'"\'\'\'', '0', '-6', '70000000000000', '888.92']
#     '''
#     if val is None:
#         return 'null'
#     elif isinstance(val, (unicode,str)):
#         return "'"+val.replace("'","''")+"'"
#     else: # elif isinstance(val, (int,long,Decimal)):
#         return str(val)

def checklen(pwd,length=8):
    return len(pwd)>=int(length)

def checkContainUpper(pwd):
    pattern = re.compile('[A-Z]+')
    match = pattern.findall(pwd)
    if match:
        return True
    else:
        return False

def checkContainNum(pwd):
    pattern = re.compile('[0-9]+')
    match = pattern.findall(pwd)
    if match:
        return True
    else:
        return False

def checkContainLower(pwd):
    pattern = re.compile('[a-z]+')
    match = pattern.findall(pwd)
    if match:
        return True
    else:
       return False

def checkSymbol(pwd):
    pattern = re.compile('([^a-z0-9A-Z])+')
    match = pattern.findall(pwd)
    if match:
        return True
    else:
        return False

def checkPassword(pwd,length=8,partten='Aa0#'):
    #判断密码长度是否合法
    lenOK=checklen(pwd,length)
    #判断是否包含大写字母
    upperOK=checkContainUpper(pwd) if partten.find('A')>=0 else True
    #判断是否包含小写字母
    lowerOK=checkContainLower(pwd) if partten.find('a')>=0 else True
    #判断是否包含数字
    numOK=checkContainNum(pwd) if partten.find('0')>=0 else True
    #判断是否包含符号
    symbolOK=checkSymbol(pwd) if partten.find('#')>=0 else True
    print lenOK , upperOK , lowerOK , numOK , symbolOK
    return (lenOK and upperOK and lowerOK and numOK and symbolOK)
def getPasswordParttenSummary(pass_partten):
    if pass_partten and pass_partten.find(':')>=0:
        length,partten = pass_partten.split(':')[0],pass_partten.split(':')[1]
        L = []
        if partten.find('A')>=0:
            L.append('大写字母')
        if partten.find('a')>=0:
            L.append('小写字母')
        if partten.find('0')>=0:
            L.append('数字')
        if partten.find('#')>=0:
            L.append('特殊字符')
        summary = '密码至少%s个字符'%(length)
        if L:
            summary += '，必须包括：'+'、'.join(L)
        return length,partten, summary
    else:
        return 0,'',''

def sorted_by_pinyin(iterable,key=lambda x:x):
    ''' 按拼音排序Unicode字符串序列，key参数指定获取元素unicode的函数 '''
    return pinyin.sorted(iterable,key)

def unpow2(x):
    '''2^n次方的反函数'''
    import math
    return int(math.log(x)/math.log(2))

def get_399001(yyyymdd):
    '''获取指定日期的深成指成交金额'''
    import formatting
    hqdate = formatting.get_yyyy_mm_dd(yyyymdd)
    url = 'http://www.szse.cn/szseWeb/FrontController.szse?ACTIONID=7&AJAX=AJAX-TRUE&CATALOGID=1826&txtDmorjc=399001&txtDate=%s&txtEndDate=%s&TABKEY=tab1&tab1PAGENUM=1'%(hqdate,hqdate)
    try:
        retval = sendPostRequest(url,{})
        if isinstance(retval,unicode):
            retval = retval.decode('gbk')
        # <tr bgcolor='#ffffff'>
        #     <td align='center'>2017-01-26</td>
        #     <td align='center'>399001</td>
        #     <td align='center'>深证成指</td>
        #     <td align='right'>9,977.963</td>
        #     <td align='right'>10,052.050</td>
        #     <td align='right'>0.740</td>
        #     <td align='right'>55,512,813,701.58</td>
        # </tr>
        #解析出成交金额，格式如上
        if isinstance(retval,basestring):
            retval = retval.replace(' ','')
            retval = retval[retval.find("<trbgcolor='#ffffff'>"):]
            retval = retval[:retval.find("</tr>")]
            pos = retval.find("<tdalign='right'>")
            while pos>=0:
                retval = retval[pos+17:]
                pos = retval.find("<tdalign='right'>")
            retval = formatting.html2text(retval).replace(',','')
    except Exception, e:
        retval = str(e)
        traceback.print_exc()
    return retval

if __name__ == "__main__":
    import doctest
    doctest.testmod()