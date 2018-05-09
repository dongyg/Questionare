#-*- encoding: utf-8 -*-

from config import *

import cadmin, cservice, cwxjsapi

from models import mforweixin, mqsnaire, mdb

urls = (
    '',                 'Index',
    'daemon',           'ForWeiXinServer',  #接收和响应微信服务器的请求
    'debug',            'CtrlDebug',
    'admin',            cadmin.app_urls,
    'rst',              cservice.app_urls,
    'jsapi',            cwxjsapi.app_urls,
    #以下界面可以从微信公号授权登录跳转进入，使用微信授权和随机数结合控制访问
    'link',             'CtrlQsnaireLink',  #答卷界面
    'p12',              'CtrlTakpartin',    #已答问卷界面
    'p13',              'CtrlWinDetail',    #中奖记录界面
    'createqs',         'CtrlCreateQsnaire',#创建空白问卷界面
    'nopay1',           'CtrlCreateNopay',  #创建普通问卷界面
    'paid1',            'CtrlCreatePaid',   #创建有奖问卷界面
    'hong1',            'CtrlCreateHong',   #创建红包问卷界面
    'p23',              'CtrlMyQsnaire',    #我发布的问卷界面
    'p31',              'CtrlMyInfomation', #设置个人信息界面
    'pmc2',             'CtrlMyCoin',       #我的调查币
    #其它界面不从微信公号授权登录跳转进入，使用随机数控制访问
    'answer',           'CtrlIncludeFSCheck', #答卷页面
    'question',         'CtrlIncludeFSCheck', #设置问卷题目
    'qstmpl',           'CtrlIncludeFSCheck', #题目模板
    'preview',          'CtrlIncludeFSCheck', #发布前预览问卷
    'predeploy',        'CtrlIncludeFSCheck', #选择问卷类型发布
    'stview',           'CtrlIncludeFSCheck', #查看问卷统计结果
    'nopay3',           'CtrlIncludeFSCheck', #普通问卷发布完成
    'paid3',            'CtrlIncludeFSCheck', #有奖问卷发布完成
    'hong3',            'CtrlIncludeFSCheck', #红包问卷发布完成
    'help3',            'CtrlIncludeFSCheck', #红包问卷发布完成
    'pzview',           'CtrlIncludeFSCheck', #答卷前预览问卷（只用于有奖问卷，或者说有图文描述的问卷）
    'help1_1',          'CtrlIncludeFSCheck', #用于通用的创建问卷后设置有奖问卷奖品信息
    'help1_2',          'CtrlIncludeFSCheck', #用于通用的创建问卷后设置红包问卷红包信息
    'help1_3',          'CtrlIncludeFSCheck', #用于通用的创建问卷后设置互助问卷调查币信息
    #话题
    'topic1',           'CtrlTopicLink',      #发话题问卷
    'newfromtp',        'CtrlCreateQsByTmpl', #复刻指定模板创建新问卷
    #营销推广
    'market',           'CtrlMarket',
    #微信号设置业务域名时需要的验证
    'MP_verify_fG9i7kmPBZtPei9T.txt',   'CtrlMPVerify',
    #不需要控制访问身份的页面
    '.*',               'viewController',
)

app_urls = web.application(urls, locals())

################################################################################
class Index:
    def GET(self):
        # return 'This is a signature checker for WEIXIN.'
        pagedata = {'HTTP_USER_AGENT': web.ctx.env.get('HTTP_USER_AGENT','')}
        put_static_host(pagedata)
        if web.ctx and web.ctx.host and web.ctx.host.startswith('jpkc.aifetel.c'):
            return web.redirect('http://jpkc.aifetel.cc:8128')
        return view_render.about(pagedata)
        # return 'It works'

class CtrlDebug:
    def GET(self):
        param = web.input()
        if web.config.sysenv_debug or wxcode=='test':
            read_config()
            random_value = cacher_random_checker.genRandomValueForFSID(param.get('fsid','30515173'))
            render = get_render(view_render,'debug')
            pagedata = {'random_value':random_value,'fsid':param.get('fsid','30515173'),'app_configuration':web.config.app_configuration}
            if web.config.cache_mode not in ('redis','memcached'):
                pagedata['cacher_random_checker'] = cacher_random_checker
                pagedata['cacher_fsobj_count'] = cacher_fans_obj.count()
            put_static_host(pagedata)
            return render(pagedata)
        else:
            pagedata = {}
            chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
            if chkret: return getPageError('页面不存在！')
            from models import madmin
            if pagedata['FSOBJ'].FS_ID in madmin.get_administrators():
                read_config()
                random_value = cacher_random_checker.genRandomValueForFSID(pagedata['FSOBJ'].FS_ID)
                render = get_render(view_render,'debug')
                pagedata['random_value'] = random_value
                if web.config.cache_mode not in ('redis','memcached'):
                    pagedata['cacher_random_checker'] = cacher_random_checker
                    pagedata['cacher_fsobj_count'] = cacher_fans_obj.count()
                pagedata['app_configuration'] = web.config.app_configuration
                pagedata['fsid'] = pagedata['FSOBJ'].FS_ID
                return render(pagedata)
            else:
                return getPageError('页面不存在！')

class ForWeiXinServer:
    """接收微信服务器请求"""
    def GET(self):
        param = web.input(signature=None,timestamp=None,nonce=None,echostr='')
        return mforweixin.checkSignature(param.signature,param.timestamp,param.nonce,param.echostr)
    def POST(self):
        """微信发来的数据包都是POST请求"""
        retval = ''
        param = web.input(signature=None,timestamp=None,nonce=None,echostr='')
        xmldata = web.data()
        if mforweixin.checkSignature(param.signature,param.timestamp,param.nonce,param.echostr)=='':
            retval = mqsnaire.treatReciveMessage(xmldata)
        return retval

def getPageError(msg,pagedata={},allowShare=False):
    mqsnaire.injectAD(pagedata) #向提示页面注入广告
    return get_render(view_render,'error')(msg,pagedata,allowShare)

################################################################################
#所有会通过微信授权跳转进来的页面，用微信授权和随机数结合校验的方式校验
#这些页面包括：link,p12,p13,nopay1,paid1,hong1,p23,p31。topic1可能
def check_WeixinAuth_or_FSIDR(param,pagedata):
    '''微信授权和随机数结合校验。param为web请求参数。pagedata为准备向页面传送的变量'''
    pagedata['HTTP_USER_AGENT'] = web.ctx.env.get('HTTP_USER_AGENT','')
    pagedata['REALHOME'] = web.ctx.get('realhome','')
    pagedata['APPID'] = wxaccount.APPID
    pagedata['WXCODE'] = wxcode
    pagedata['signPackage'] = web.Storage(mforweixin.calc_jsapi_signature(web.ctx.homedomain+web.ctx.env['REQUEST_URI']))
    put_static_host(pagedata)
    #尝试从微信授权跳回获取用户身份
    if param.has_key('code') and param['code']:
        webtoken,fsid,isfan = mforweixin.get_webtoken(param.code,param.get('state'))
    else:
        webtoken,fsid,isfan = '',None,False
    #如果上面没有获取到用户身份，用输入参数fsid获取用户身份，并用r校验
    if not fsid: # or not isfan:
        fsid = param.get('fsid')
        if not (param.get('r') and cacher_random_checker.chkRandomValueNotPop(fsid,param['r'])):
            return getPageError('链接已失效！',pagedata)
    if fsid:
        pagedata['FSOBJ'] = mdb.get_fans_byfsid(fsid)
        if str(fsid) in web.config.app_configuration.get('run:blacklist',[]):
            return getPageError('您的账号出现异常操作，已暂时锁定！',pagedata)
    if not pagedata.get('FSOBJ'):
        return getPageError('获取用户信息失败！',pagedata)
    isfan = bool(pagedata['FSOBJ'].SUBSCRIBE)
    pagedata['r'] = cacher_random_checker.genRandomValueForFSID(fsid) #为页面传入一个新的r
    #如果还没有获取到用户身份或fsid+r校验不通过，返回提示页面
    if not fsid: # or not isfan:
        return getPageError('链接已失效！',pagedata)

#link
class CtrlQsnaireLink:
    def GET(self):
        '''用于问卷参与页面。微信网页登录授权后跳转进来时，需要按照微信网页开发方法执行后续动作，用户已经授权或未授权'''
        #有几种情况进入此页面：
        #1.粉丝在公号内获取到问卷参与链接，这个链接分享给其他粉丝也是可用的，不是粉丝的话用不了。https://open.weixin.qq.com/connect/oauth2/authorize?appid=wxaa70b76f1dcc6401&redirect_uri=https%3A%2F%2Fqsnaire.aifetel.cc%2Flink&response_type=code&scope=snsapi_userinfo&state=b4166c68c46611e69acd9cf387b1feac#wechat_redirect
        #2.直接链接。link?state=QN_ID
        #2.1.微信公号网页授权后跳转进来，带code,state参数，再根据code参数可获取到用户openid
        #2.2.用户把带code参数的链接分享出去，此时code参数是无效的，获取不到用户openid
        #2.3.用户直接分享不带code参数的链接，此时获取不到用户身份
        # 微信公号网页授权http://mp.weixin.qq.com/wiki/17/c0f37d5704f0b64713d5d2c37b468d75.html
        # 第一步：用户同意授权，获取code
        # 第二步：通过code换取网页授权access_token，此时可拿到openid和unionid
        # 第三步：刷新access_token（如果需要）
        # 第四步：拉取用户信息(需scope为 snsapi_userinfo)
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        pagedata['QNOBJ'] = mdb.get_naire(param.get('state'))
        if not pagedata['QNOBJ']:
            return getPageError('问卷不存在！',pagedata)
        if chkret:
            if pagedata.get('FSOBJ'):
                #如果返回错误并且有用户身份，说明用户在黑名单
                return chkret
            else:
                #答卷页面针对取不到身份的用户（返回错误无用户身份）
                #如果用户是在微信内访问，重定向到微信网页授权页面，从而可以让他进入答卷页面。否则返回关注提示和问卷基本信息页面
                if pagedata['HTTP_USER_AGENT'].find('MicroMessenger')>0:
                    return web.seeother(mforweixin.get_mp_authurl("%s/link"%(HOST_NOS),pagedata['QNOBJ'].QN_ID),True)
                else:
                    return get_render(view_render,'tipsub')(pagedata)
        #判断问卷是否有效和在回收中
        if pagedata['QNOBJ'].QN_STATUS==3:
            return getPageError('该问卷目前暂停回收！',pagedata)
        elif pagedata['QNOBJ'].QN_STATUS<2:
            return getPageError('该问卷不在回收中！',pagedata)
        elif pagedata['QNOBJ'].QN_STATUS!=2:
            return getPageError('该问卷已结束！',pagedata)
        ANOBJ = mdb.get_answer(pagedata['QNOBJ'].QN_ID,pagedata['FSOBJ'].FS_ID)
        anshint = mdb.get_anshint(pagedata['FSOBJ'],pagedata['QNOBJ'],ANOBJ)
        if anshint:
            return getPageError(anshint,pagedata, True)
        if pagedata['QNOBJ'].QN_TYPE==1:
            return get_render(view_render,'pzview')(pagedata)
        else:
            return get_render(view_render,'answer')(pagedata)

#p12
class CtrlTakpartin():
    def GET(self):
        '''已答问卷界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['QNLST'] = mdb.list_partin(pagedata['FSOBJ'].FS_ID)
        render = get_render(view_render,'partin')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#p13
class CtrlWinDetail():
    def GET(self):
        '''中奖记录界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['QNLST'] = mdb.list_award(pagedata['FSOBJ'].FS_ID)
        pagedata['QNID'] = param.get('state','')
        render = get_render(view_render,'award')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#createqs
class CtrlCreateQsnaire():
    def GET(self):
        '''创建空白问卷。通用的问卷创建，有奖/红包/互助/普通都是这一个入口，录入问卷基本信息、录入题目、选择发布方式、然后再付款。'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if param.has_key('qnid'):
            if param['qnid'].startswith(('sojump_')):
                param['qnid'] = hashlib.md5(param['qnid']).hexdigest()
            pagedata['QNOBJ'] = mdb.get_naire(param['qnid'])
        render = get_render(view_render,'createqs')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#nopay1
class CtrlCreateNopay():
    def GET(self):
        '''创建普通问卷界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if param.has_key('qnid'):
            pagedata['QNOBJ'] = mdb.get_naire(param['qnid'])
        render = get_render(view_render,'nopay1')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#paid1
class CtrlCreatePaid():
    def GET(self):
        '''创建有奖问卷界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if param.has_key('qnid'):
            pagedata['QNOBJ'] = mdb.get_naire(param['qnid'])
        render = get_render(view_render,'paid1')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#hong1
class CtrlCreateHong():
    def GET(self):
        '''创建红包问卷界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if param.has_key('qnid'):
            pagedata['QNOBJ'] = mdb.get_naire(param['qnid'])
        render = get_render(view_render,'hong1')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#p23
class CtrlMyQsnaire():
    def GET(self):
        '''我发布的问卷界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['QNLST'] = mdb.list_myaire(pagedata['FSOBJ'].FS_ID)
        render = get_render(view_render,'myaire')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

#p31
class CtrlMyInfomation():
    def GET(self):
        '''设置个人信息界面'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        render = get_render(view_render,'mine')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

class CtrlMyCoin:
    def GET(self):
        '''我的调查币'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['FSOBJ']['COIN_LEVEL'] = mdb.get_fans_level(pagedata['FSOBJ'])
        pagedata['FSOBJ']['COIN_DETAIL'] = mdb.list_coin(pagedata['FSOBJ'].FS_ID)
        pagedata['COIN_RANK'] = mdb.stat_lastweek_coin()
        render = get_render(view_render,'pmc2')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

################################################################################
#所有不会通过微信授权跳转的页面，只使用随机数校验方式
def check_FSIDR_and_QN(param,pagedata):
    '''随机数校验。param为web请求参数。pagedata为准备向页面传送的变量'''
    pagedata['HTTP_USER_AGENT'] = web.ctx.env.get('HTTP_USER_AGENT','')
    pagedata['REALHOME'] = web.ctx.get('realhome','')
    pagedata['APPID'] = wxaccount.APPID
    pagedata['WXCODE'] = wxcode
    pagedata['signPackage'] = web.Storage(mforweixin.calc_jsapi_signature(web.ctx.homedomain+web.ctx.env['REQUEST_URI']))
    put_static_host(pagedata)
    fsid = param.get('fsid')
    random_value = param.get('r')
    if not fsid:
        return getPageError('获取用户信息失败！',pagedata)
    if str(fsid) in web.config.app_configuration.get('run:blacklist',[]):
        return getPageError('您的账号出现异常操作，已暂时锁定！',pagedata)
    if not (random_value and cacher_random_checker.chkRandomValueNotPop(fsid,random_value)):
        return getPageError('链接已失效！')
    pagedata['FSOBJ'] = mdb.get_fans_byfsid(fsid)
    if not pagedata.get('FSOBJ'):
        return getPageError('获取用户信息失败！',pagedata)
    pagedata['QNOBJ'] = mdb.get_naire(param.get('qnid'))
    if not pagedata['QNOBJ']:
        return getPageError('问卷不存在！',pagedata)
    pagedata['r'] = cacher_random_checker.genRandomValueForFSID(fsid) #为页面传入一个新的r

class CtrlIncludeFSCheck:
    def GET(self):
        #支持: answer,question,qstmpl,preview,stview,nopay3,paid3,hong3,help1_1,help1_2,help1_3，这些是需要FSOBJ和QNOBJ和r的。
        #备注: paid2,hong2在cwxjsapi中实现，因为微信支付要求在二级目录下。在cwxjsapi中实现相同的 check_FSIDR_and_QN 和 CtrlIncludeFSCheck 处理
        param = web.input()
        urlpars = urlparse.urlparse(web.ctx.path)
        ctxpath = urlpars.path
        render = get_render(view_render,ctxpath)
        if not render:
            return getPageError('页面不存在！',pagedata)
        #向页面传入数据
        pagedata = {}
        chkret = check_FSIDR_and_QN(param,pagedata)
        if chkret: return chkret
        #问卷类型与访问页面不匹配，认定为问卷不存在
        if ctxpath.endswith(('paid2')) and pagedata['QNOBJ'].QN_TYPE!=1:
            return getPageError('问卷不存在！',pagedata)
        if ctxpath.endswith(('hong2')) and pagedata['QNOBJ'].QN_TYPE!=2:
            return getPageError('问卷不存在！',pagedata)
        if ctxpath.endswith(('help2')) and pagedata['QNOBJ'].QN_TYPE!=3:
            return getPageError('问卷不存在！',pagedata)
        if ctxpath.endswith('stview'): #在统计结果页面为传话题问卷
            pagedata['TPOBJ'] = mdb.get_naire(pagedata['QNOBJ'].TOPIC_QNID) if pagedata['QNOBJ'].TOPIC_QNID else None
        pagedata["MESSAGE"] = cacher_message_pool.pop(pagedata['FSOBJ'].FS_ID)
        return render(pagedata)

################################################################################
class viewController:
    def GET(self):
        #支持: faq,about
        param = web.input()
        urlpars = urlparse.urlparse(web.ctx.path)
        ctxpath = urlpars.path
        render = get_render(view_render,ctxpath)
        if not render:
            return getPageError('页面不存在！')
        if not ctxpath.endswith(('faq','about','test')):
            return getPageError('页面不存在！')
        # if ctxpath.endswith(('test')):
        #     web.debug('-'*20)
        # expiration = datetime.datetime.now() + datetime.timedelta(days=36500)
        # web.setcookie('kudou_user_weixin', '13', expires=expiration.strftime("%a, %d-%b-%Y %H:%M:%S PST"))
        pagedata = {'HTTP_USER_AGENT': web.ctx.env.get('HTTP_USER_AGENT',''), 'PARAMS':param}
        put_static_host(pagedata)
        return render(pagedata)

################################################################################
class CtrlTopicLink:
    def GET(self):
        '''创建话题问卷，可直接创建：提供参数fsid/r/tpic。也可从微信网页授权进入：传入参数state'''
        #支持: topic1
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['TPOBJ'] = mdb.get_naire(param.get('tpid')) if param.has_key('tpid') else mdb.get_naire(param.get('state'))
        if not pagedata['TPOBJ']:
            return getPageError('无效的问卷话题！',pagedata)
        if pagedata['TPOBJ'].QN_STATUS!=99:
            return getPageError('无效的问卷话题！',pagedata)
        pagedata['QNOBJ'] = mdb.get_naire(param.get('qnid'))
        pagedata['REFQN'] = mdb.get_naire(param.get('refqn'))
        render = get_render(view_render,'topic1')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)

class CtrlCreateQsByTmpl:
    def GET(self):
        '''复刻指定模板创建新问卷'''
        #这个方法是先显示模板题目，再填写问卷基本信息
        param = web.input()
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        pagedata['TPOBJ'] = mdb.get_naire(param.get('tpid')) if param.has_key('tpid') else mdb.get_naire(param.get('state'))
        if not pagedata['TPOBJ']:
            return getPageError('无效的问卷模板！',pagedata)
        if pagedata['TPOBJ'].QN_STATUS<10: #所有模板类问卷都可以
            return getPageError('无效的问卷模板！',pagedata)
        pagedata['REFQN'] = mdb.get_naire(param.get('refqn'))
        render = get_render(view_render,'newfromtp')
        return render(pagedata) if render else getPageError('页面不存在！',pagedata)


################################################################################
class CtrlMarket:
    def GET(self):
        '''营销人员查看自己的二维码和推广统计数据。非营销人员申请加入营销计划'''
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        from models import madmin
        if pagedata['FSOBJ'].FS_ID not in madmin.get_salers():
            pagedata['tipmsg'] = mqsnaire.applyMarketing(pagedata['FSOBJ'].FS_ID)
        if pagedata['FSOBJ'].FS_ID in madmin.get_salers():
            pagedata['SALQR'] = madmin.get_market_qr(pagedata['FSOBJ'].FS_ID)
            pagedata['MDLST'] = madmin.get_market_byfs(pagedata['FSOBJ'].FS_ID)
        render = get_render(view_render,'marketing')
        return render(pagedata) if render else getPageError('页面不存在！')

################################################################################
class CtrlMPVerify:
    def GET(self):
        '''用于微信公号平台内设置服务器地址时的校验'''
        file_object = open('static/MP_verify_fG9i7kmPBZtPei9T.txt', 'rb')
        web.header('Content-Type', 'application/x-xls; charset=UTF-8')
        web.header("Content-Disposition","attachment;filename=MP_verify_fG9i7kmPBZtPei9T.txt")
        return file_object.read()

