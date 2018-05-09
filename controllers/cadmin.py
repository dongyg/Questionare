#-*- encoding: utf-8 -*-

from config import *

from models import mforweixin, mqsnaire, mdb, madmin

urls = (
    '/prelottery',  'CtrlPreviewLottery',
    '/endlottery',  'CtrlFinishLottery',
    '/chartdaily',  'CtrlViewChartDaily',
    '/mngmarket',   'CtrlManagerMarket',
    '/paymarket',   'CtrlPayMarket',
    '/bawj',        'CtrlBaWenjuanXing',
    '/pasojump',    'CtrlSpiderSojump',
    '/sycntoqs',    'CtrlSyncQsToServer',
    '/uploadqs',    'CtrlUploadQs',
    '/.*',          'viewController',
)

app_urls = web.application(urls, locals())

################################################################################
def getPageError(msg):
    return get_render(view_render,'error')(msg)

################################################################################
class CtrlPreviewLottery:
    def GET(self):
        '''摇号预览'''
        from cpublic import check_WeixinAuth_or_FSIDR
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if pagedata['FSOBJ'].FS_ID not in madmin.get_administrators():
            return getPageError('页面不存在！')
        render = get_render(admin_render,'prelottery')
        if not render:
            return getPageError('页面不存在！')
        pagedata['QNLST'] = madmin.list_prelotqs()
        return render(pagedata)
    def POST(self):
        '''采用某个摇号方案'''
        param = web.input(r='',fsid='',qnid='',addnum=0,hqrq='')
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return '{"error":"无效请求！"}'
        if int(param['fsid']) not in madmin.get_administrators():
            return '{"error":"无效请求！"}'
        retval = madmin.set_lottery(param['qnid'],int(param['hqrq']),int(param['addnum']))
        return formatting.json_string(retval)

class CtrlFinishLottery:
    def POST(self):
        '''将问卷设置为已开奖/兑奖结束状态。主要用于结束那些自己发的用于测试的问卷。'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"无效请求！"}'
        if int(param['fsid']) not in madmin.get_administrators():
            return '{"error":"无效请求！"}'
        today = datetime.datetime.today().strftime("%Y%m%d")
        retval = mdb.set_qsend(param['qnid'],today,2)
        return formatting.json_string(retval)

class CtrlViewChartDaily:
    def GET(self):
        '''查看日统计数据的走势图'''
        from cpublic import check_WeixinAuth_or_FSIDR
        param = web.input(d='7')
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if pagedata['FSOBJ'].FS_ID not in madmin.get_administrators():
            return getPageError('页面不存在！')
        render = get_render(admin_render,'chartdaily')
        if not render:
            return getPageError('页面不存在！')
        if not str(param.d).isdigit():
            param.d = '7'
        pagedata['STDAILY'] = madmin.list_daily(param.d)
        return render(pagedata,param)

class CtrlManagerMarket:
    def GET(self):
        from cpublic import check_WeixinAuth_or_FSIDR
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if pagedata['FSOBJ'].FS_ID not in madmin.get_administrators():
            return getPageError('页面不存在！')
        render = get_render(admin_render,'mngmarket')
        if not render:
            return getPageError('页面不存在！')
        pagedata['STMARKET'] = madmin.list_market()
        return render(pagedata,param)

class CtrlPayMarket:
    def POST(self):
        param = web.input(r='',fsid='',yyyymmdd='',busiid=0)
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"无效请求！"}'
        if int(param['fsid']) not in madmin.get_administrators():
            return '{"error":"无效请求！"}'
        retval = madmin.pay_market(param['yyyymmdd'],int(param['busiid']))
        return formatting.json_string(retval)

class CtrlBaWenjuanXing:
    def GET(self):
        '''扒问卷页面'''
        from cpublic import check_WeixinAuth_or_FSIDR
        param = web.input()
        pagedata = {}
        chkret = check_WeixinAuth_or_FSIDR(param,pagedata)
        if chkret: return chkret
        if pagedata['FSOBJ'].FS_ID not in web.config.app_configuration['run:selfman']:
            return getPageError('页面不存在！')
        render = get_render(admin_render,'bawj')
        if not render:
            return getPageError('页面不存在！')
        return render(pagedata,param)
class CtrlSpiderSojump:
    def GET(self):
        '''扒之'''
        param = web.input(fsid='',r='',wjid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"无效请求！"}'
        if int(param['fsid']) not in web.config.app_configuration['run:selfman']:
            return '{"error":"无效请求！"}'
        import_qnobj = {}
        if param.wjid:
            qnid = 'sojump_'+param.wjid
            qnid = hashlib.md5(qnid).hexdigest()
            if mdb.get_naire(qnid):
                return u"%s 已存在！可以去编辑！"%qnid
            print qnid
            resp = utils.sendGetRequest('https://sojump.com/m/%s.aspx'%param.wjid)
            import_qnobj = madmin.decode_sojump_html(qnid,resp)
            retdat = madmin.save_sojump(import_qnobj,param['fsid'])
            if retdat.has_key('error'):
                return retdat['error']
        return formatting.json_string(import_qnobj,ensure_ascii=False,pretty=True)

class CtrlSyncQsToServer:
    def POST(self):
        '''针对测试机使用。将指定问卷传到正式服务器，不支持问卷所带图片。r是测试机的随机数，rup是用户填写的自己在正式机上的随机数'''
        param = web.input(fsid='',r='',rup='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"无效请求！"}'
        if int(param['fsid']) not in web.config.app_configuration['run:selfman']:
            return '{"error":"无效请求！"}'
        if not param.rup:
            return '{"error":"无效R值！"}'
        qsjson = mdb.export_naire(param.qnid)
        if qsjson:
            data = {'fsid':param.fsid,'r':param.rup,'json':qsjson}
            resp = utils.sendPostRequest('https://qsnaire.aifetel.cc/admin/uploadqs',data) #
            return resp
        else:
            return '{"error":"无效问卷！"}'

class CtrlUploadQs:
    def POST(self):
        '''针对正式机使用。通过上传的json导入问卷。'''
        param = web.data() #fsid='',r='',json=''
        try:
            param = json.loads(param)
        except Exception, e:
            return '{"error":"%s"}'%str(e)
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"无效请求R！"}'
        if int(param['fsid']) not in web.config.app_configuration['run:selfman']:
            return '{"error":"无效请求身份！"}'
        if not param.get('json'):
            return '{"error":"无效数据！"}'
        retval = madmin.save_sojump(json.loads(param['json']))
        return formatting.json_string(retval)

################################################################################
class viewController:
    def GET(self):
        #支持: faq,about
        param = web.input()
        urlpars = urlparse.urlparse(web.ctx.path)
        ctxpath = urlpars.path[1:]
        print ctxpath
        render = get_render(admin_render,ctxpath)
        if not render:
            return getPageError('页面不存在！')
        # if not ctxpath.endswith(('faq','about')):
        #     return getPageError('页面不存在！')
        pagedata = {'HTTP_USER_AGENT': web.ctx.env.get('HTTP_USER_AGENT','')}
        put_static_host(pagedata)
        if ctxpath.endswith('viewerr') and param.get('state'):
            pagedata['logrec'] = mforweixin.get_logs(param.get('state'))
        return render(pagedata,param)
