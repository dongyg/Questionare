# -*- coding: utf-8 -*-

import web
from web import net
import json, time, traceback

import strip_html
import re, urlparse, datetime, urllib, types, decimal

def brief_format_date(d):
    '''将日期时间格式化为简易格式。当天的只留时分秒，昨天的添加昨天字样，再往前的为yyyy-mm-dd hh:nn格式'''
    try:
        if isinstance(d,basestring):
            d = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        days = (datetime.date.today() - datetime.datetime.date(d)).days
        if days==0:
            return format_date(d,'%H:%M:%S')
        elif days==1:
            return '昨天 '+format_date(d,'%H:%M')
        else:
            return format_date(d,'%Y-%m-%d %H:%M')
    except Exception, e:
        traceback.print_exc()
        return format_date(d,'%Y-%m-%d %H:%M')

def date_add(days,d=None):
    '''在指定日期上计算加减天数'''
    if not d: d = datetime.date.today()
    return d + datetime.timedelta(days=days)

def format_date(d, f):
    try:
        if isinstance(d,basestring):
            d = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        return d.strftime(f)
    except:
        traceback.print_exc()
        return d

def calc_datetime_range(d1,d2=None):
    '''计算两个时间差，返回秒数'''
    try:
        if not d2:
            d2 = datetime.datetime.now()
        if not d1:
            d1 = d2
        elif isinstance(d1,basestring):
            d1 = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
        return (d2-d1).seconds
    except:
        traceback.print_exc()
        return 0

def format_date2(val):
    '''
        >>> format_date2(20160614)
        '2016-06-14'
    '''
    try:
        val = str(val)
        time.strptime(val, "%Y%m%d")
        syear = val[0:4]
        smonth = val[4:6]
        sday = val[6:8]
        return syear+'-'+smonth+'-'+sday
    except Exception as e:
        traceback.print_exc()
        return val

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

def isfloat(value):
    import re
    s = str(value)
    match = re.match(r'^-?(\d+)(\.(\d*))?$',s)
    return bool(match)

def format_money(value, scale=0):
    '''  '''
    if value is None:
        return ''
    if isinstance(value,(float,int,long)):
        s = ('%.'+str(scale)+'f') % value # 四舍五入
    elif isinstance(value, decimal.Decimal):
        s = format_Decimal(value,scale)
    else:
        s = str(value)
    match = re.match(r'^-?(\d+)(\.(\d*))?$',s)
    if not match:
        return s
    integral = match.group(1)
    fractional = match.group(3) or ''
    t = ''
    for i in xrange(len(integral)):
        if i%3==0 and i:
            t = ',' + t
        t = integral[-1-i] + t
    if len(fractional) > scale:
        fractional = fractional[:scale]
    else:
        fractional += '0'*(scale-len(fractional))
    if fractional:
        t += '.' + fractional
    if s.startswith('-'):
        t = '-' + t
    return t

def format_Decimal(d, scale=None):
    # assert isinstance(d, decimal.Decimal)
    if not d.is_finite():
        return str(d)
    if scale is not None:
        d = d.quantize(decimal.Decimal(10)**-scale) # 四舍五入，结果为小数点后scale位
    sign, digits, exp = d.as_tuple()
    if exp >= 0:
        s = ''.join((str(d) for d in digits)) + '0'*exp
    else:
        exp = -exp
        n = len(digits)
        if exp < n:
            s = ''.join((str(d) for d in digits[:n-exp])) \
                    + '.' + ''.join((str(d) for d in digits[n-exp:]))
        else:
            s = '0.' + '0'*(exp-n) + ''.join((str(d) for d in digits))
    if sign:
        s = '-' + s
    return s

def format_chn_money(money):
    ''' "1,001,001,100.00" -> u"壹拾亿零壹佰万壹仟壹佰元整"
      要求 0 <= money < 1万亿 '''
    if isinstance(money,basestring):
        money = money.replace(',','')
    if not isinstance(money,float):
        try:
            money = float(money)
        except:
            traceback.print_exc()
            return str(money)
    money = '%.2f' % money
    idx = money.find('.')
    integral, fractional = money[:idx], money[idx+1:]
    negative = integral.startswith('-')
    if negative:
        integral = integral[1:]
    chn_digits = u'零壹贰叁肆伍陆柒捌玖'
    chn_units = (u'仟',u'佰',u'拾',u'')
    s = ''
    def format_four_digits(four_digits):
        # assert four_digits > '0000'
        s = ''
        for i,digit in enumerate(four_digits):
            digit = int(digit)
            if digit:
                if s and s[-1]!=chn_units[i-1]:
                    s += u'零'
                s += chn_digits[digit] + chn_units[i]
        return s

    four_digits = integral[-12:-8]
    if int(four_digits or '0'):
        four_digits = '0'*(4-len(four_digits)) + four_digits
        s += format_four_digits(four_digits) + u'亿'
    four_digits = integral[-8:-4]
    if int(four_digits or '0'):
        if s and four_digits[0]=='0':
            s += u'零'
        four_digits = '0'*(4-len(four_digits)) + four_digits
        s += format_four_digits(four_digits) + u'万'
    four_digits = integral[-4:]
    if int(four_digits or '0'):
        if s and (s[-1]==u'亿' or four_digits[0]=='0'):
            s += u'零'
        four_digits = '0'*(4-len(four_digits)) + four_digits
        s += format_four_digits(four_digits)
    if not s:
        s = u'零'
    s += u'元'
    if fractional == '00':
        s += u'整'
    else:
        digit = int(fractional[0])
        if digit:
            s += chn_digits[digit] + u'角'
        digit = int(fractional[1])
        if digit:
            s += chn_digits[digit] + u'分'
    if negative:
        s = u'负' + s
    return s

def url_quote(url):
    return urllib.quote_plus(url.encode('utf8')).decode('utf8')

def cut_length(s, max=40):
    if len(s) > max:
        s = s[0:max] + '...'
    return s

def get_nice_url(url):
    host, path = urlparse.urlparse(url)[1:3]
    if path == '/':
        path = ''
    return cut_length(host+path)

def text2html(s):
    s = html_quote(s)
    s = replace_links(s)
    s = replace_breaks(s)
    s = replace_indents(s)
    return s
def html2text(h):
    import strip_html
    return strip_html.strip(h)

def replace_breaks(s):
    return re.sub('\n', '<br/>', s)

def replace_indents(s):
    s = re.sub('\t', 4*' ', s)
    return re.sub('\s{2,}', '&nbsp;', s)

def replace_links(s):
    return re.sub('(http://[^\s]+)',
        lambda m: '<a class="commentLink" rel="nofollow" href="%s">%s</a>' % (m.group(1), get_nice_url(m.group(1))),
        s, re.I)

# we may want to get months ago as well
def how_long(d):
    return web.datestr(d, datetime.datetime.now())

def httpdate(date):
    return web.httpdate(date)

def html_quote(text):
    return net.htmlquote(text)

def html_quote_plus(text):
    text = html_quote(text)
    text = text.replace(' ', '&nbsp;')
    return text

def html_unquote(html):
    return net.htmlunquote(html)

def html_unquote_plus(html):
    html = html_unquote(html)
    html = html.replace('&nbsp;', ' ')
    return html

def nice_text(text):
    return text.replace('-', '--') \
               .replace('’', '\'') \
               .replace('“', '"')  \
               .replace('”', '"')

def strip_tags(html):
    html = html_unquote_plus(html)
    html = strip_html.strip(html)
    return html
    return nice_text(html)

def unpow2(x):
    '''2^n次方的反函数'''
    import math
    return int(math.log(x)/math.log(2))

def json_string(obj,pretty=False,ensure_ascii=True):
    """将dict或list转换为json字符串。pretty:是否格式化。ensure_ascii:是否转换unicode为编码形式"""
    import utils
    if pretty:
        return json.dumps(obj,cls=utils.DateTimeJSONEncoder,ensure_ascii=ensure_ascii,indent=4)
    else:
        return json.dumps(obj,cls=utils.DateTimeJSONEncoder,ensure_ascii=ensure_ascii,separators=(',',':'))
def json_object(text,default={}):
    """将json字符串转换为dict或list对象"""
    if not text: return default
    try:
        return json.loads(text)
    except Exception, e:
        return {}

def width_minibtn_string(text):
    """返回字符串在界面上mini btn上所需要的宽度，一个ASCII字符5px,btn边缘26px"""
    import re
    return int(len(re.sub("\\\u\w{4}", 'AA', json.dumps(text)))*5) + 26
def count_true(t):
    '''计算输入tuple中有几个True'''
    return len([x for x in t if x])
def get_keyword():
    """得到一个基于时间戳的uuid并替换首位数字为字母并去掉中间的-号的字符串"""
    import uuid
    uusd = str(uuid.uuid1())
    if uusd[0] in ('0','1','2','3','4','5','6','7','8','9'):
        uusd = chr(ord(uusd[0])+63)+uusd[1:]
    return uusd.replace('-','')
def base64encode(dat):
    """将输入字符串编码为Base64"""
    import base64
    return base64.b64encode(dat)
def base64decode(b64dat):
    """将输入Base64编码解码"""
    import base64
    return base64.b64decode(b64dat)
def formatFileSize(fsize):
    '''格式化字节数'''
    if fsize < 1024:
        return str(fsize)+'B'
    elif fsize < 1024*1024:
        return '%.2fKB' % (float(fsize)/1024)
    elif fsize < 1024*1024*1024:
        return '%.2fMB' % (float(fsize)/1024/1024)
    else:
        return '%.2fGB' % (float(fsize)/1024/1024/1024)
def ceil(v):
    import math
    return math.ceil(v)
def websafe(s):
    return web.websafe(s)

def ascSafeString(s):
    '''把unicode转换成\uxxxx的形式。对于emoji表情，这样可以保存到utf8的mysql数据库中。返回【u'\U0001f600'】的形式，使用字符串时再使用eval转换回来'''
    return repr(s) if isinstance(s,unicode) and s!='' else s
def unAscSafeString(s):
    '''使用eval把u'\U0001f600'形式的字符串转换成unicode字符串'''
    return eval(s) if s and isinstance(s,basestring) and s.startswith(("u'",'u"')) else s
def replaceEmoji(sss):
    '''替换字符串中的Emoji字符为[Emoji]字样'''
    # sss = u'I have a dog \U0001f436 . You have a cat \U0001f431 ! I smile \U0001f601 to you!'
    import re
    try:
        # Wide UCS-4 build
        myre = re.compile(u'['
            u'\U0001F300-\U0001F64F'
            u'\U0001F680-\U0001F6FF'
            u'\u2600-\u2B55]+',
            re.UNICODE)
    except re.error:
        # Narrow UCS-2 build
        myre = re.compile(u'('
            u'\ud83c[\udf00-\udfff]|'
            u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
            u'[\u2600-\u2B55])+',
            re.UNICODE)
    # print myre.findall(sss)         # 找出字符串中的Emoji
    retval = myre.sub('[Emoji]', sss)  # 替换字符串中的Emoji
    return html2text(retval)

def des_encrypt(data,key):
    '''DES加密，密文Base64编码以保证ASCII字符'''
    import binascii
    import base64
    import pyDes
    k = pyDes.triple_des(str(key), pyDes.CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=pyDes.PAD_PKCS5)
    d = k.encrypt(str(data))
    d = base64.encodestring(d)
    return d.strip()
def des_decrypt(data,key):
    '''DES解密，密文是Base64编码要先解码'''
    import binascii
    import base64
    import pyDes
    k = pyDes.triple_des(str(key), pyDes.CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=pyDes.PAD_PKCS5)
    data = base64.decodestring(data)
    d = k.decrypt(data)
    return d

def compress_string(raw_data):
    import zlib
    zb_data = zlib.compress(raw_data)
    print "len(raw_data)=%d, len(zb_data)=%d, compression ratio=%.2f"\
        % (len(raw_data), len(zb_data), float(len(zb_data))/len(raw_data))
    return zb_data

def decompress_string(zb_data):
    import zlib
    raw_data = zlib.decompress(zb_data)
    return raw_data

def get_tid_by_openid(openid):
    '''将OPENID做des加密后再base64编码'''
    return des_encrypt(openid,'abe4550df95a4273b8710217')
def get_openid_by_tid(tid):
    '''将tid做base64解码后再做des解密，得到openid'''
    return des_decrypt(tid,'abe4550df95a4273b8710217')

def get_status_title(qnstatus):
    '''返回问卷状态文字'''
    if qnstatus==0:
        return '编辑中'
    elif qnstatus==1:
        return '审批中'
    elif qnstatus==2:
        return '正在回收'
    elif qnstatus==3:
        return '暂停回收'
    elif qnstatus==8:
        return '已作废'
    elif qnstatus==9:
        return '已结束'
def get_coin_title(chgtype):
    if chgtype==11:
        return '关注'
    elif chgtype==12:
        return '完善资料'
    elif chgtype==13:
        return '签到'
    elif chgtype==14:
        return '答问卷'
    elif chgtype==15:
        return '答卷奖励'
    elif chgtype==19:
        return '问卷结余'
    elif chgtype==21:
        return '发问卷'
    elif chgtype==22:
        return '补扣'
    elif chgtype==23:
        return '出售'
    elif chgtype==24:
        return '抽奖'
    elif chgtype==25:
        return '兑换'

def get_multiple(multiple,yyyymmdd=None):
    '''从yyyymmdd.n的字符串中解析出n'''
    if not yyyymmdd:
        yyyymmdd = date_add(-1).strftime("%Y%m%d")
    if multiple and multiple.startswith(yyyymmdd):
        mltp = multiple.split('.')[1]
        mltp = int(mltp) if mltp.isdigit() and int(mltp)>0 else 1
    else:
        mltp = 1
    return mltp

def square(n):
    '''平方数列'''
    retval = []
    for i in xrange(1,n+1):
        retval.append(i**2)
    return retval
def cube(n):
    '''立方数列'''
    retval = []
    for i in xrange(1,n+1):
        retval.append(i**3)
    return retval

def fibo1(n):
    '''斐波拉契数列，实现1'''
    stack=[]
    if n==0 or n==1:
        return 1
    else:
        stack.append(1)
        stack.append(1)
        for i in xrange(2,n):
            stack.append(stack[i-1]+stack[i-2])
        return stack

def fibo2(n):
    '''斐波拉契数列，实现2'''
    x,y = 0,1
    retval = []
    while y<n:
        retval.append(y)
        x,y = y,x+y
    return retval

def fibo3(n):
    '''斐波拉契数列，实现3'''
    def fib():
        x,y = 0,1
        while True:
            yield x
            x,y = y,x+y
    import itertools
    return list(itertools.islice(fib(),n))

def get_sojump_id(url):
    '''输入url：https://sojump.com/m/13404722.aspx，返回问卷id'''
    import re
    retval = re.sub('\.aspx$', '',url)
    while retval.find('/')>=0:
        retval = retval[retval.find('/')+1:]
    return retval
