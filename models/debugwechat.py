#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *

def get_token():
    """获取ACCESS_TOKEN"""
    #http://mp.weixin.qq.com/wiki/index.php?title=获取access_token
    if wxaccount['expires']<=int(time.time()): #如果当前保存的AccessToken已过期就获取新的
        rurl = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"%(wxaccount['appid'],wxaccount['appsecret'])
        import urllib2
        response = urllib2.urlopen(rurl).read()
        try:
            response = json.loads(response)
        except Exception, e:
            traceback.print_exc()
            wxaccount['accesstoken'] = ''
        else:
            wxaccount['accesstoken'] = response.get('access_token','')
            wxaccount['expires'] = int(response.get('expires_in','0'))+int(time.time())
            print 'New token:', wxaccount['accesstoken']
            print 'Expires:', wxaccount['expires']
    return wxaccount['accesstoken']

def define_menus():
    """自定义菜单"""
    #http://mp.weixin.qq.com/wiki/index.php?title=自定义菜单创建接口
    accesstoken = get_token()
    if not accesstoken:
        return None
    #微信服务器不接受\uxxxx编码
    import urllib2,urllib
    menus = wxaccount['menus']
    rurl = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token=%s"%(accesstoken)
    if os.name=='nt':
        response = urllib2.urlopen(rurl, urllib.urlencode(json.loads(menus)))
    else:
        response = urllib2.urlopen(rurl, menus)
    content = response.read()
    return content

def get_qrwithparam(weixincode,sceneid=0,LIMIT=False):
    """生成带参数的二维码"""
    #http://mp.weixin.qq.com/wiki/index.php?title=生成带参数的二维码
    accesstoken = get_token()
    if not accesstoken:
        return None
    #微信服务器不接受\uxxxx编码
    import urllib2,urllib,base64
    rurl = "https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token=%s"%(accesstoken)
    if not sceneid:
        sceneid = int(time.time())
    if LIMIT:
        data = {"expire_seconds": 1800, "action_name": "QR_LIMIT_SCENE", "action_info": {"scene": {"scene_id": sceneid}}}
    else:
        data = {"expire_seconds": 1800, "action_name": "QR_SCENE", "action_info": {"scene": {"scene_id": sceneid}}}
    req = urllib2.Request(rurl)
    data = json.dumps(data)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    response = opener.open(req, data)
    content = response.read()
    try:
        retdata = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return {'errcode': 99999, 'errmsg': str(e)}
    else:
        if retdata.has_key('ticket'):
            retval = set_qrscene(weixincode,sceneid,retdata['ticket'],retdata['expire_seconds'])
            rurl = "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=%s"%(retdata['ticket'])
            response = urllib2.urlopen(rurl)
            content = response.read()
            return {"sceneid":sceneid,"qrdata":base64.b64encode(content),"url":rurl}
        else:
            return retdata

def sendTextMessage(openid,msgtxt):
    """发送客服消息，文本消息"""
    #http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息
    accesstoken = get_token()
    if not openid:
        return 'No User: %s'%openid
    data = '''{"touser":"%s", "msgtype":"text", "text":{"content":"%s"}}'''%(openid,msgtxt)
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"%(accesstoken)
    response = urllib2.urlopen(rurl, data)
    content = response.read()
    try:
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        if not retval['errcode']:
            return 'Send success.'
        else:
            print retval
            return retval['errmsg']

def sendLinkRTMessage(openid,articles):
    """发送外链图文消息"""
    #http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息
    accesstoken = get_token()
    if not openid:
        return 'No User: %s'%openid
    data = {"touser":openid, "msgtype":"news", "news":{"articles":[]}}
    if isinstance(articles,list):
        data['news']['articles'].extend(articles)
    elif isinstance(articles,dict):
        data['news']['articles'].append(articles)
    else:
        return 'Parameter [articles] must be list/dict.'
    data = json.dumps(data, ensure_ascii=False)
    import urllib2,urllib
    rurl = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"%(accesstoken)
    response = urllib2.urlopen(rurl, data)
    content = response.read()
    try:
        retval = json.loads(content)
    except Exception, e:
        traceback.print_exc()
        return str(e)
    else:
        if not retval['errcode']:
            return ''
        else:
            return content


def test():
    # get_token()
    # print define_menus()
    # print sendTextMessage('olJ2zuADCnfNFhGimO_6ggECTvTs',time.time())
    # print sendTextMessage('olJ2zuADCnfNFhGimO_6ggECTvTs','今天还可创建1个，去<a href="http://localhost:8000">创建</a>') #超链不正常显示
    # print sendLinkRTMessage('olJ2zuADCnfNFhGimO_6ggECTvTs',MSG_WELCOME)
    pass

