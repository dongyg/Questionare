#-*- encoding: utf-8 -*-
#微信支付等jsapi用。因为微信要求在二级目录下
#备注: paid2,hong2在这里实现，因为微信支付要求在二级目录下。实现与cpublic相同的 check_FSIDR_and_QN 和 CtrlIncludeFSCheck 处理

from config import *

from models import mforweixin, mqsnaire, mdb

urls = (
    '/paid2',            'CtrlIncludeFSCheck', #有奖问卷付保证金
    '/hong2',            'CtrlIncludeFSCheck', #红包问卷付红包款
    '/help2',            'CtrlIncludeFSCheck', #互助问卷付调查币
    '/paynotify',        'CtrlTreatWxpayCallback', #异步接收微信支付结果通知的回调地址
)

app_urls = web.application(urls, locals())

################################################################################
def getPageError(msg):
    return get_render(view_render,'error')(msg)

################################################################################
#所有不会通过微信授权跳转的页面，只使用随机数校验方式
def check_FSIDR_and_QN(param,pagedata):
    '''随机数校验。param为web请求参数。pagedata为准备向页面传送的变量'''
    pagedata['HTTP_USER_AGENT'] = web.ctx.env.get('HTTP_USER_AGENT','')
    pagedata['REALHOME'] = web.ctx.get('realhome','')
    pagedata['APPID'] = wxaccount.APPID
    fsid = param.get('fsid')
    random_value = param.get('r')
    if not fsid:
        return getPageError('获取用户信息失败！')
    if not (random_value and cacher_random_checker.chkRandomValueNotPop(fsid,random_value)):
        return getPageError('链接已失效！')
    pagedata['FSOBJ'] = mdb.get_fans_byfsid(fsid)
    if not pagedata.get('FSOBJ'):
        return getPageError('获取用户信息失败！')
    pagedata['QNOBJ'] = mdb.get_naire(param.get('qnid'))
    if not pagedata['QNOBJ']:
        return getPageError('问卷不存在！')
    pagedata['r'] = cacher_random_checker.genRandomValueForFSID(fsid) #为页面传入一个新的r

class CtrlIncludeFSCheck:
    def GET(self):
        #paid2,hong2在这里实现，因为微信支付要求在二级目录下。help2也在这里，为了保持相同结构。在cwxjsapi中实现相同的 check_FSIDR_and_QN 和 CtrlIncludeFSCheck 处理
        param = web.input()
        urlpars = urlparse.urlparse(web.ctx.path)
        ctxpath = urlpars.path[1:]
        render = get_render(view_render,ctxpath)
        if not render:
            return getPageError('页面不存在！')
        #向页面传入数据
        pagedata = {}
        chkret = check_FSIDR_and_QN(param,pagedata)
        if chkret: return chkret
        #问卷类型与访问页面不匹配，认定为问卷不存在
        if ctxpath.endswith(('paid2')) and pagedata['QNOBJ'].QN_TYPE!=1:
            return getPageError('问卷不存在！')
        if ctxpath.endswith(('hong2')) and pagedata['QNOBJ'].QN_TYPE!=2:
            return getPageError('问卷不存在！')
        if ctxpath.endswith(('help2')) and pagedata['QNOBJ'].QN_TYPE!=3:
            return getPageError('问卷不存在！')
        if ctxpath.endswith('answer'):
            pagedata['signPackage'] = web.Storage(mforweixin.calc_jsapi_signature(web.ctx.homedomain+web.ctx.env['REQUEST_URI']))
        elif ctxpath.endswith(('paid2','hong2','help2')):
            pagedata['signPackage'] = web.Storage(mforweixin.cacl_jsapi_wxpay_sign(pagedata['QNOBJ'].PREPAY_ID,web.ctx.homedomain+web.ctx.env['REQUEST_URI']))
        return render(pagedata)

class CtrlTreatWxpayCallback:
    def POST(self):
        '''异步接收微信支付结果通知并处理'''
        #https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_7
        retval = []
        param = web.input()
        xmldata = web.data()
        retdat = mqsnaire.treatWxpayNotify(xmldata)
        if retdat.has_key('error'):
            retval.append({'return_code':'FAIL'})
            retval.append({'return_msg':retdat['error']})
        else:
            retval.append({'return_code':'SUCCESS'})
        return mforweixin.toXml(retval,'xml')


