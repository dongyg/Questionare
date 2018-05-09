#!/usr/bin/env python
#-*- encoding: utf-8 -*-

#重要提示：向微信发送客服消息时，article里面的字符串都不能是unicode

# 公用的，为支持微信公众号，与微信服务器交互的功能，与业务无关。wxcode, wxaccount 为全局变量
# MSG_WELCOME = {"title":"问卷调查大师欢迎你", "url":"http://localhost:8000/about", "description":"做最专业的有奖问卷调查系统。\n在这里，你可以：\n1.免费发布调查问卷，无偿有偿任意选。最重要的是：你不用自己分发问卷\n2.参与问卷调查获得抽取有偿报酬的机会\n\n不参加也有机会哦！猛击“阅读全文”"}
# MENUS = {
#   "button": [
#     {
#       "name": "答问卷",
#       "sub_button": [
#         { "name": "我要答卷", "type": "click", "key": "M11" },
#         { "name": "已答问卷", "type": "click", "key": "M12" },
#         { "name": "馅饼砸中", "type": "click", "key": "M13" }
#       ]
#     },
#     {
#       "name": "发问卷",
#       "sub_button": [
#         { "name": "创建普通问卷", "type": "click", "key": "M21" },
#         { "name": "创建有奖问卷", "type": "click", "key": "M22" },
#         { "name": "我发布的问卷", "type": "click", "key": "M23" }
#       ]
#     },
#     {
#       "name": "用户中心",
#       "sub_button": [
#         { "name": "我的信息", "type": "click", "key": "M31" },
#         { "name": "帮助中心", "type": "view", "url": "http://localhost:8000/faq" },
#         { "name": "关于",    "type": "view", "url": MSG_WELCOME['url'] }
#       ]
#     }
#   ]
# }
# wxcode = 'test'
# wxaccount = web.Storage({
#     "ORIGINAL_ID": 'gh_c450d6f36741',
#     "APPID": 'wxaa70b76f1dcc6401',
#     "APPSECRET": '3722f877c77ac618a127791e3eb34f6d',
#     "TOKEN": 'dongyg_Aifetel',
#     "ACCESSTOKEN": 'I8xEhdF0W98piBKGFWewDZ_51r2NzFwrRDd58x7_FaRXRTQhLga-1ZI3A8xebXSRXzijLSXzPSaNccF7Q7N_HbrwYh0BhoXVsR-WbKSqfyELLTaAAAZZH',
#     "EXPIRES": 1481476841,
#     "JSAPI_TICKET": "",
#     "JSAPI_EXPIRES": 0,
#     "WEBTOKEN": '',
#     "WEBEXPIRES": 0,
#     "MCH_ID": "",
#     "WXPAY_KEY": "",
#     "MENUS": json.dumps(MENUS, ensure_ascii=False)
# })

from config import *

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

################################################################################
# 工具函数
def is_not_none(params):
    """判断dict是否为空"""
    for k, v in params.items():
        if v is None:
            return False
    return True

def toJson(xml_body):
    """XMl To JSON"""
    #http://docs.python.org/2/library/xml.etree.elementtree.html#xml.etree.ElementTree.XML
    json_data = {}
    root = ET.fromstring(xml_body)
    for child in root:
        if child.tag == 'CreateTime':
            value = long(child.text.strip()) if child.text else ''
        else:
            value = child.text.strip() if child.text else ''
        json_data[child.tag] = value
    return json_data

def addCdata(data):
    """转CDATA格式"""
    #http://stackoverflow.com/questions/174890/how-to-output-cdata-using-elementtree
    if type(data) is str or type(data) is unicode:
        return '<![CDATA[%s]]>' % data.replace(']]>', ']]]]><![CDATA[>')
    return data

def toXml(xml_data, wrap_tag=None, cdata=True):
    """JSON To XMl"""
    xml = ''
    if wrap_tag:
        xml = '<%s>' % wrap_tag
    for item in xml_data:
        tag = item.keys()[0]
        value = item.values()[0]
        value = addCdata(value) if cdata else value
        value = value.encode('utf8') if type(value)==unicode else value
        xml += '<%s>%s</%s>' % (tag, value, tag)
    if wrap_tag:
        xml += '</%s>' % wrap_tag
    return xml

def checkWeixinResponse(resp):
    '''检查微信服务器返回是否包含错误'''
    if resp.get('errcode',0)!=0:
        return False
    return True


################################################################################
#微信服务交互
def checkSignature(signature,timestamp,nonce,echostr):
    """验证信息是否来自微信"""
    #http://mp.weixin.qq.com/wiki/index.php?title=接入指南
    #加密/校验流程：
    #1. 将token、timestamp、nonce三个参数进行字典序排序
    #2. 将三个参数字符串拼接成一个字符串进行sha1加密
    #3. 开发者获得加密后的字符串可与signature对比，标识该请求来源于微信
    #4. 确认此次GET请求来自微信服务器后，原样返回echostr参数内容，则接入生效，否则接入失败。
    params = {
        'token': wxaccount.TOKEN,
        'timestamp': timestamp,
        'nonce': nonce
    }
    if is_not_none(params):
        sort_params = sorted([v for k, v in params.items()])
        client_signature = hashlib.sha1(''.join(sort_params)).hexdigest()
        if client_signature == signature:
            return echostr
    return "This is Check Signature for WEIXIN [%s]"%wxcode


################################################################################
#token/ticket与授权
def get_token(force=False):
    """获取ACCESS_TOKEN"""
    #http://mp.weixin.qq.com/wiki/index.php?title=获取access_token
    if wxaccount.EXPIRES<=int(time.time()-60): #如果当前保存的AccessToken已过期就获取新的，提前60秒
        rurl = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"%(wxaccount.APPID,wxaccount.APPSECRET)
        import urllib2
        response = urllib2.urlopen(rurl).read()
        try:
            response = json.loads(response)
        except Exception, e:
            traceback.print_exc()
            wxaccount.ACCESSTOKEN = ''
            wxaccount.EXPIRES = 0
        else:
            if response.get('access_token'):
                wxaccount.ACCESSTOKEN = str(response.get('access_token',''))
                wxaccount.EXPIRES = int(response.get('expires_in','0'))+int(time.time())
                set_accesstoken(wxcode,wxaccount.ACCESSTOKEN,wxaccount.EXPIRES)
            else:
                # print '-'*20,json.dumps(response)
                wxaccount.ACCESSTOKEN = ''
                wxaccount.EXPIRES = 0
    return wxaccount.ACCESSTOKEN
def get_jsapi_ticket():
    '''获取jsapi_ticket'''
    if wxaccount.JSAPI_EXPIRES<=int(time.time()-60): #如果当前保存的JSAPI_TICKET已过期就获取新的，提前60秒
        rurl = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=%s&type=jsapi"%(get_token())
        import urllib2
        response = urllib2.urlopen(rurl).read()
        try:
            response = json.loads(response)
        except Exception, e:
            traceback.print_exc()
            wxaccount.JSAPI_TICKET = ''
            wxaccount.JSAPI_EXPIRES = 0
        else:
            if response.get('ticket'):
                wxaccount.JSAPI_TICKET = str(response.get('ticket',''))
                wxaccount.JSAPI_EXPIRES = int(response.get('expires_in','0'))+int(time.time())
                set_jsapi_ticket(wxcode,wxaccount.JSAPI_TICKET,wxaccount.JSAPI_EXPIRES)
            else:
                # print '-'*20,json.dumps(response)
                wxaccount.JSAPI_TICKET = ''
                wxaccount.JSAPI_EXPIRES = 0
    return wxaccount.JSAPI_TICKET
def get_webtoken(code,state):
    """换取网页授权access_token。scope=snsapi_base时返回access_token的同时就有openid"""
    #http://mp.weixin.qq.com/wiki/17/c0f37d5704f0b64713d5d2c37b468d75.html
    fsid,isfan = None,False
    rurl = "https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code"%(wxaccount.APPID,wxaccount.APPSECRET,code)
    import urllib2
    response = urllib2.urlopen(rurl).read()
    try:
        response = json.loads(response)
    except Exception, e:
        traceback.print_exc()
        wxaccount.WEBTOKEN = ''
        wxaccount.WEBEXPIRES = 0
    else:
        if response.get('access_token'):
            wxaccount.WEBTOKEN = response.get('access_token','')
            wxaccount.WEBEXPIRES = int(response.get('expires_in','0'))+int(time.time())
            #没有用网页授权的webtoken去获取用户信息，暂不保存，否则每次写数据库，没必要
            # set_oauthtoken(wxcode,wxaccount.WEBTOKEN,wxaccount.WEBEXPIRES)
            if response.get('openid'):
                # fsid,isfan = set_weixinfan(response.get('openid'),{'UNIONID':response.get('unionid')})
                import mqsnaire
                fsid,isfan = set_weixinfan(response.get('openid'),{'IN_BY':mqsnaire.getStateBusinessID(state),'UNIONID':response.get('unionid')},False)
                #不需要网页拉取微信用户信息
        else:
            # print '-'*20,json.dumps(response)
            wxaccount.WEBTOKEN = ''
            wxaccount.WEBEXPIRES = 0
    return wxaccount.WEBTOKEN,fsid,isfan
def calc_jsapi_signature(url):
    '''为JSAPI计算signature。返回signPackage为包含 timestamp, noncestr, signature 的字典'''
    noncestr = utils.get_random_string(10)
    timestamp = str(int(time.time()))
    string1 = "jsapi_ticket=%s&noncestr=%s&timestamp=%s&url=%s"%(get_jsapi_ticket(),noncestr,timestamp,url)
    signature = hashlib.sha1(string1).hexdigest()
    return {'noncestr':noncestr, 'timestamp':timestamp, 'signature':signature}
#网页授权
def get_mp_authurl(url,state='',scope='snsapi_base'):
    '''为指定url生成微信公号网页授权url。scope取值:snsapi_base/snsapi_userinfo'''
    import urllib
    redirect = urllib.quote(url).replace('/','%2F') #将重定向url进行encode
    authurl = "https://open.weixin.qq.com/connect/oauth2/authorize?appid=%s&redirect_uri=%s&response_type=code&scope=%s&state=%s#wechat_redirect"
    return authurl%(wxaccount.APPID,redirect,scope,state)

def get_fanslist(fromopenid=''):
    '''获取用户列表'''
    # https://api.weixin.qq.com/cgi-bin/user/get?access_token=ACCESS_TOKEN&next_openid=NEXT_OPENID
    rurl = "https://api.weixin.qq.com/cgi-bin/user/get?access_token=%s&next_openid=%s"%(get_token(),fromopenid)
    import urllib2
    response = urllib2.urlopen(rurl).read()
    try:
        response = json.loads(response)
    except Exception, e:
        traceback.print_exc()
        return e
    else:
        return response

################################################################################
#公号管理：菜单/用户/二维码
def define_menus(menus):
    """自定义菜单。输入为没有unicode编码的json字符串"""
    # http://mp.weixin.qq.com/wiki/index.php?title=自定义菜单创建接口
    #微信服务器不接受\uxxxx编码
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token=%s"%(get_token())
    response = urllib2.urlopen(rurl, menus)
    content = response.read()
    return content
def get_qrwithparam(sceneid=0,LIMIT=False):
    """生成带参数的二维码"""
    #http://mp.weixin.qq.com/wiki/index.php?title=生成带参数的二维码
    #微信服务器不接受\uxxxx编码
    import urllib2,urllib,base64
    from helpers import utils
    rurl = "https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token=%s"%(get_token())
    if not sceneid:
        sceneid = utils.get_id_bytime(1)
    if LIMIT: #永久二维码，不过期，目前为最多10万个，sceneid只支持1-100000
        data = {"action_name": "QR_LIMIT_SCENE", "action_info": {"scene": {"scene_id": sceneid}}}
    else:     #临时二维码，30天（即2592000秒）后过期，sceneid为32位非0整型
        data = {"expire_seconds": 2592000, "action_name": "QR_SCENE", "action_info": {"scene": {"scene_id": sceneid}}}
    data = json.dumps(data, ensure_ascii=False)
    try:
        req = urllib2.Request(rurl)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        response = opener.open(req, data)
        content = response.read()
        retdata = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return {'errcode': 99999, 'errmsg': str(e)}
    else:
        if retdata.has_key('ticket'):
            retdata['sceneid'] = sceneid
        return retdata
def get_fansinfo(openid):
    '''获取用户基本信息'''
    # https://api.weixin.qq.com/cgi-bin/user/info?access_token=ACCESS_TOKEN&openid=OPENID&lang=zh_CN
    rurl = "https://api.weixin.qq.com/cgi-bin/user/info?access_token=%s&openid=%s&lang=zh_CN"%(get_token(),openid)
    import urllib2
    try:
        response = urllib2.urlopen(rurl).read()
        response = json.loads(response)
    except Exception, e:
        traceback.print_exc()
    else:
        if checkWeixinResponse(response):
            set_fansinfo(response)
        else:
            set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'ERROR', content=json.dumps(response))


################################################################################
#微信消息相关
def replyText(from_user, to_user, reply_msg):
    """回复文字信息。打包成微信服务器接收的XML格式"""
    if to_user and reply_msg:
        response_msg = toXml([
            {'ToUserName': to_user},
            {'FromUserName': from_user},
            {'CreateTime': int(time.time())},
            {'MsgType': 'text'},
            {'Content': reply_msg}
        ], 'xml')
    else:
        response_msg = ''
    return response_msg

def replyArticle(from_user, to_user, article_data):
    """回复图文信息格式。打包成微信服务器接收的XML格式"""
    article_count = len(article_data)
    atricle_xml = '<xml>'
    base_xml_data = toXml([
            {'ToUserName': to_user},
            {'FromUserName': from_user},
            {'CreateTime': int(time.time())},
            {'MsgType': 'news'},
            {'ArticleCount': article_count}
        ])
    atricle_xml += base_xml_data
    atricle_xml += '<Articles>'
    for atricle in article_data:
        item_xml = toXml([
            {'Title': atricle.get('title')},
            {'Description': atricle.get('description')},
            {'PicUrl': atricle.get('picurl')},
            {'Url': atricle.get('url')}
        ], 'item')
        atricle_xml += item_xml
    atricle_xml += '</Articles>'
    atricle_xml += '</xml>'
    return atricle_xml

def sendTextMessage(openid,msgtxt):
    """发送客服消息，文本消息"""
    #http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息
    accesstoken = get_token()
    data = {"touser":str(openid), "msgtype":"text", "text":{"content":msgtxt.encode('utf8') if isinstance(msgtxt,unicode) else msgtxt}}
    data = json.dumps(data, ensure_ascii=False)
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"%(accesstoken)
    try:
        if web.config.sysenv_debug:
            set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'text', content=msgtxt)
        response = urllib2.urlopen(rurl, data)
        content = response.read()
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        if not retval['errcode']:
            return ''
        else:
            # set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'ERROR', content=content)
            return retval['errmsg']

def sendLinkRTMessage(openid,articles):
    """发送客服消息，外链图文消息"""
    #http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息
    accesstoken = get_token()
    data = {"touser":str(openid), "msgtype":"news", "news":{"articles":[]}}
    if isinstance(articles,list):
        data['news']['articles'].extend([x for x in articles if x]) #去掉空字典
    elif isinstance(articles,dict) and articles:
        data['news']['articles'].append(articles)
    else:
        return 'Parameter [articles] must be list/dict.'
    for x in data['news']['articles']:
        if x.has_key('title') and isinstance(x['title'],unicode):
            x['title'] = x['title'].encode('utf8')
        if x.has_key('description') and isinstance(x['description'],unicode):
            x['description'] = x['description'].encode('utf8')
        if x.has_key('picurl') and isinstance(x['picurl'],unicode):
            x['picurl'] = x['picurl'].encode('utf8')
        if x.has_key('url') and isinstance(x['url'],unicode):
            x['url'] = x['url'].encode('utf8')
    data = json.dumps(data, ensure_ascii=False)
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"%(accesstoken)
    try:
        if web.config.sysenv_debug:
            set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'news', content=json.dumps(articles))
        response = urllib2.urlopen(rurl, data)
        content = response.read()
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        if not retval['errcode']:
            return ''
        else:
            # set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'ERROR', content=content)
            return content

def listMaterials(offset=0,count=1):
    '''获取素材列表'''
    import urllib2,urllib
    rurl = 'https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=%s'%get_token()
    data = {"type":'news',"offset":offset,"count":count}
    data = json.dumps(data, ensure_ascii=False)
    try:
        response = urllib2.urlopen(rurl,data)
        content = response.read()
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        return content

def sendMPNews(openid,media_id):
    '''发送客服消息，图文消息（点击跳转到图文消息页面） ，传入素材ID'''
    accesstoken = get_token()
    data = {"touser":str(openid), "msgtype":"mpnews", "mpnews":{"media_id":media_id}}
    data = json.dumps(data, ensure_ascii=False)
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"%(accesstoken)
    try:
        if web.config.sysenv_debug:
            set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'mpnews', content=data)
        response = urllib2.urlopen(rurl, data)
        content = response.read()
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        if not retval['errcode']:
            return ''
        else:
            set_logs(wxaccount.ORIGINAL_ID, openid, int(time.time()), 'ERROR', content=content)
            return retval['errmsg']


################################################################################
#客服功能
#新版客服功能，客服只能在网页版在线客服接收和回复消息，暂不支持手机
# https://mpkf.weixin.qq.com/
# http://kf.qq.com/faq/120911VrYVrA160316Jf6jaQ.html
def replyCustomerService(from_user, to_user, kfaccount='kf2001@diaochadashi'):
    """回复文字信息。打包成微信服务器接收的XML格式。回复这个消息后，微信服务器会将客户发来的消息发到客服"""
    if to_user:
        response_msg = toXml([
            {'ToUserName': to_user},
            {'FromUserName': from_user},
            {'CreateTime': int(time.time())},
            {'MsgType': 'transfer_customer_service'}
        ], 'xml')
    else:
        response_msg = ''
    return response_msg
def list_customer():
    '''获取客服基本信息'''
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/customservice/getkflist?access_token=%s"%(get_token())
    response = urllib2.urlopen(rurl)
    content = response.read()
    return content

################################################################################
#微信支付
def calc_wxpay_signature(data):
    '''计算微信支付签名。输入签名前的json格式参数。输出签名'''
    d1 = dict([(k,v) for k,v in data.items() if v]) #去掉空值项
    L = d1.keys()
    L.sort()
    d2 = [(k,d1[k]) for k in L] #根据key按ASCII码从小到大排序
    d2.append(('key',wxaccount.WXPAY_KEY))
    stringSignTemp = '&'.join(['%s=%s'%(k,v.encode('utf8') if type(v)==unicode else v) for k,v in d2]) #拼接成字符串stringSignTemp
    sign = hashlib.md5(stringSignTemp).hexdigest().upper()
    return sign
def get_wxpay_signed_package(data):
    '''为微信支付生成包含名称的报文。输入签名前的json格式参数。输出xml格式报文'''
    sign = calc_wxpay_signature(data)
    data['sign'] = sign
    d1 = [{k:v} for k,v in data.items()]
    return toXml(d1,'xml',False)
def cacl_jsapi_wxpay_sign(prepayid,url):
    '''为JSAPI的微信支付功能生成计算签名。返回包含签名的整个参数包'''
    data = {
        "appId": wxaccount.APPID,
        "timeStamp": str(int(time.time())),
        "nonceStr": utils.get_random_string(10),
        "package": "prepay_id=%s"%prepayid,
        "signType": "MD5"
    }
    sign = calc_wxpay_signature(data)
    data['paySign'] = sign
    return data
def wxpay_unifiedorder(title,tradeno,fee,billip,openid):
    '''统一下单。输入：商品描述，商户订单号，订单总金额(单位元)，用户端IP，OPENID。输出：sucess:微信支付统一下单返回的预支付交易会话标识，或error:错误消息'''
    data = {"appid": wxaccount.APPID,
            "mch_id": wxaccount.MCH_ID,
            "nonce_str": utils.get_random_string(30),
            "sign_type": "MD5",
            "body": title,
            "out_trade_no": tradeno,
            "total_fee": int(fee*100),
            "spbill_create_ip": billip,
            "notify_url": "%s/jsapi/paynotify"%HOST_SSL,
            "trade_type": "JSAPI",
            "openid": openid
    }
    data = get_wxpay_signed_package(data)
    import urllib2,urllib
    rurl = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    try:
        response = urllib2.urlopen(rurl, data)
        content = response.read()
        retval = toJson(content)
    except Exception, e:
        traceback.print_exc()
        return {'error':str(e)}
    else:
        if retval.get('return_code','')!='SUCCESS':
            return {'error':retval.get('return_msg','未知错误')}
        sign = retval.pop('sign','')
        if cmp(sign,calc_wxpay_signature(retval)):
            return {'error':'验证微信支付返回签名错'}
        if retval.get('result_code','')!='SUCCESS':
            return {'error':retval.get('err_code_des','未知错误')}
        return {'success':retval['prepay_id']}
def checkWxpayNotify(xml_body):
    '''检查微信支付结果通知'''
    set_logs('WEIXIN','PAY',content=xml_body)
    data = toJson(xml_body)
    if data.get('return_code','')!='SUCCESS':
        return {'error':data.get('return_msg')}
    sign = data.pop('sign','')
    if cmp(sign,calc_wxpay_signature(data)):
        return {'error':'验证微信支付通知签名错'}
    if data.get('result_code','')!='SUCCESS':
        return {'error':data.get('err_code_des','未知错误')}
    return {'success':data}

def sendHongbao(openid,amount,billno,actname,wishing,remark,clientip):
    '''向指定用户发红包，输入：OPENID,红包金额(单位元2位小数)'''
    #https://pay.weixin.qq.com/wiki/doc/api/tools/cash_coupon.php?chapter=13_4&index=3
    if amount<1 or amount>200:
        return {'error':'普通红包必须在1-200元之间'}
    data = {
        "nonce_str": utils.get_random_string(30),
        "mch_billno": wxaccount.MCH_ID+billno,
        "mch_id": wxaccount.MCH_ID,
        "wxappid": wxaccount.APPID,
        "send_name": "营恒国际",
        "re_openid": openid,
        "total_amount": int(round(amount*100,0)), #int(amount*100), 不知道为什么 int(2.28*100)=227，先round掉再int()就是228
        "total_num": 1,
        "wishing": wishing,
        "client_ip": clientip,
        "act_name": actname,
        "remark": remark
    }
    data = get_wxpay_signed_package(data)
    import urllib2,urllib,ssl
    rurl = "https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack"
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cafile = "./ssl/rootca.pem")
        context.load_cert_chain('./ssl/apiclient_cert.pem','./ssl/apiclient_key.pem','1439205402')
        response = urllib2.urlopen(rurl, data, context=context)
        content = response.read()
        set_logs('WEIXIN','RED',content=content)
        retval = toJson(content)
    except Exception, e:
        traceback.print_exc()
        return {'error':str(e)}
    else:
        if retval.get('return_code','')!='SUCCESS':
            return {'error':retval.get('return_msg','未知错误')}
        if retval.get('result_code','')!='SUCCESS':
            return {'error':retval.get('err_code_des','未知错误')}
        #PS:实测发现返回报文中并没有sign，但发红包文档中写着有
        return {'success':retval}


################################################################################
#信息存储到本地数据库
def set_accesstoken(weixincode,accesstoken,expires):
    """设置微信账号的AccessToken和过期时间Expires"""
    t = dbFrame.transaction()
    try:
        dbFrame.update('WX_ACCOUNT',vars=locals(),where='WEIXIN_CODE=$weixincode',ACCESSTOKEN=accesstoken,EXPIRES=expires)
    except Exception, e:
        t.rollback()
        return {"error":e}
    else:
        t.commit()
def set_oauthtoken(weixincode,webtoken,webexpires):
    """设置微信账号的OAuth access_token和过期时间expires"""
    t = dbFrame.transaction()
    try:
        dbFrame.update('WX_ACCOUNT',vars=locals(),where='WEIXIN_CODE=$weixincode',WEBTOKEN=webtoken,WEBEXPIRES=webexpires)
    except Exception, e:
        t.rollback()
        return {"error":e}
    else:
        t.commit()
def set_jsapi_ticket(weixincode,ticket,expires):
    """设置微信账号的JSAPI的ticket和过期时间expires"""
    t = dbFrame.transaction()
    try:
        dbFrame.update('WX_ACCOUNT',vars=locals(),where='WEIXIN_CODE=$weixincode',JSAPI_TICKET=ticket,JSAPI_EXPIRES=expires)
    except Exception, e:
        t.rollback()
        return {"error":e}
    else:
        t.commit()

def set_weixinfan(openid,args={},fromchat=True):
    '''设置微信用户。args里面是要设置的字段及值。fromchat表示是否源自会话等活动（这些活动都是粉丝）。返回 tuple(FSID，用户是否公号粉丝)，如果出错就返回(None,None)'''
    #微信网页授权有2种scope，都无需关注：1、以snsapi_base为scope发起的网页授权，是用来获取进入页面的用户的openid的。2、以snsapi_userinfo为scope发起的网页授权，是用来获取用户的基本信息的。
    global mutex
    import mdb
    FSOBJ = mdb.get_fans_byopenid(openid)
    # FSOBJ = web.listget(dbFrame.select("WX_FANS",vars=locals(),where="OPENID=$openid").list(), 0, None)
    t = dbFrame.transaction()
    try:
        #总是设置最近活跃时间
        args['UNSUBSCRIBETIME'] = utils.get_currdatetimestr(dbFrame.dbtype) #利用取消关注时间字段记录综合的最后活跃时间
        if fromchat:
            args['LASTACTIVETIME'] = utils.get_currdatetimestr(dbFrame.dbtype) #只记录来自会话的最后活跃时间，来自网页的不记录
        #如果显式设置关注为1，说明是关注动作，设置关注时间
        if args.get('SUBSCRIBE')==1: #关注
            args['SUBSCRIBETIME'] = utils.get_currdatetimestr(dbFrame.dbtype)
        #如果显式设置关注为0，说明是取消关注动作，设置取消关注时间
        if args.get('SUBSCRIBE')==0:
            args['UNSUBSCRIBETIME'] = utils.get_currdatetimestr(dbFrame.dbtype)
        else:
            #如果是会话/扫码等动作，并且不是取消关注动作，说明用户是粉丝，设置SUBSCRIBE以保证表中记录的关注状态是正确的。只有网页活动不知道是否粉丝
            if fromchat:
                args['SUBSCRIBE'] = 1
        isfan = args.get('SUBSCRIBE')==1
        #根据openid判断的如果存在就更新，不存在就添加
        if not FSOBJ:
            if mutex.acquire(1):
                fsid = utils.get_id_bytime()
                mutex.release()
            else:
                fsid = utils.get_id_bytime()
            while mdb.get_fans_byfsid(fsid):
                fsid = utils.get_id_bytime()
            if not args.has_key('IN_BY'):
                args['IN_BY'] = 10000
            if args.get('SUBSCRIBE')==1: #如果用户不存在，且SUBSCRIBE为1，设置关注赠送积分
                args['COIN_TOTAL'] = 100
                args['COIN_HOLD'] = 100
                dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype),CHG_AMOUNT=100,CHG_TYPE=11)
            dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$args['IN_BY']",GET_FANS=web.SQLLiteral('GET_FANS+1'))
            dbFrame.insert("WX_FANS",FS_ID=fsid,OPENID=openid,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype), **args)
        else:
            fsid = FSOBJ.FS_ID
            if FSOBJ.SUBSCRIBE!=None:
                args.pop('IN_BY','') #在修改时如果SUBSCRIBE不是null说明用户关注中或曾经关注过，不修改IN_BY的值
            elif args.get('SUBSCRIBE')==1: #如果SUBSCRIBE是null说明用户从未关注过，第1次关注的话设置赠送积分
                pass
                # args['COIN_TOTAL'] = 100
                # args['COIN_HOLD'] = 100
                # dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype),CHG_AMOUNT=100,CHG_TYPE=11)
            if FSOBJ.SUBSCRIBE==args.get('SUBSCRIBE'): #如果现存值等于即将设置值就pop掉不再设置
                args.pop('SUBSCRIBE','')
            dbFrame.update("WX_FANS",vars=locals(),where='OPENID=$openid', **args)
            # if args.keys()!=['LASTACTIVETIME']:
            #     #如果只是设置最近活跃时间，不清除缓存
            #     cacher_fans_obj.delete(fsid)
            FSOBJ.update(args) #更新缓存
            cacher_fans_obj.set(fsid,FSOBJ)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return None,None
    else:
        t.commit()
    return fsid,isfan
def set_fansinfo(data):
    '''保存从微信获取的粉丝用户信息'''
    t = dbFrame.transaction()
    try:
        openid = data['openid']
        data = {
            "NICKNAME": formatting.ascSafeString(data.get('nickname','')),
            "SEX": data.get('sex'),
            "CITY": formatting.replaceEmoji(data.get('city')),
            "PROVINCE": formatting.replaceEmoji(data.get('province')),
            "COUNTRY": data.get('country'),
            "HEADIMGURL": data.get('headimgurl'),
            "UNIONID": data.get('unionid','')
        }
        dbFrame.update('WX_FANS',vars=locals(),where="OPENID=$openid",**data)
        cacher_fsid_byopenid.delete(openid)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return e
    else:
        t.commit()

def set_logs(fromusername,tousername,createtime=int(time.time()),msgtype='',event='',eventkey='',content='',msgid='',mediaid=''):
    """记录微信消息日志"""
    retval = '0'
    if isinstance(content,basestring):
        content = formatting.replaceEmoji(content)
    t = dbFrame.transaction()
    try:
        retval = dbFrame.insert('WX_LOGS',FROMUSERNAME=fromusername,TOUSERNAME=tousername,CREATETIME=createtime,MSGTYPE=msgtype,EVENT=event,EVENTKEY=eventkey,CONTENT=content,MSGID=msgid,MEDIAID=mediaid)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return e
    else:
        t.commit()
    if fromusername=='ERROR' or msgtype=='ERROR':
        errmsg = {"title":"发生错误"+str(retval), "url":get_mp_authurl("%s/admin/viewerr"%(HOST_NOS),retval), "description":content,"picUrl":""}
        if wxcode=='diaochadashi':
            print sendLinkRTMessage('ovZQXwHJuO1LPrgefXp-oV-FsWkg',errmsg) #695423523在调查大师的openid
        else:
            print sendLinkRTMessage('olJ2zuIjHKUyDLyWsu6y0ZkPvcdA',errmsg) #695423523在test的openid
def get_logs(serialno):
    retval = web.listget(dbFrame.select("WX_LOGS",vars=locals(),where="SERIAL_NO=$serialno").list(),0,None)
    if retval:
        retval.CREATETIME = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(retval.CREATETIME))
    return retval

################################################################################
def test():
    # print get_token()
    print wxaccount.ACCESSTOKEN
    print wxaccount.EXPIRES
    print wxaccount.MENUS
    print define_menus(wxaccount.MENUS)
    # print sendTextMessage('olJ2zuADCnfNFhGimO_6ggECTvTs',time.time())
    # print sendTextMessage('olJ2zuADCnfNFhGimO_6ggECTvTs','今天还可创建1个，去<a href="http://localhost:8000">创建</a>') #超链不正常显示
    # print sendTextMessage('olJ2zuADCnfNFhGimO_6ggECTvTs',MSG_WELCOME)
    # print sendLinkRTMessage('ovZQXwJQB1vGrk8jBqXAG7qUuM7Y',{"title":"测试","url":"","description":MSG_WELCOME,"picurl":""})
    # print get_qrwithparam(int(time.time()))
