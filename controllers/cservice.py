#-*- encoding: utf-8 -*-

from config import *

from models import mqsnaire,mdb

urls = (
    '/util/city',   'UtilProvinceCity',
    '/mine',        'CtrlMine',
    '/createqs',    'CtrlCreateQsnaire',
    '/modiqs',      'CtrlModifyQsnaire',
    '/nopay',       'CtrlNoPay',
    '/paid',        'CtrlPaid',
    '/hong',        'CtrlHong',
    '/prepay',      'CtrlPrepay',
    '/image/(.+)/', 'CtrlImage',
    '/question',    'CtrlQuestion',
    '/deploy',      'CtrlDeploy',
    '/stopqs',      'CtrlStop',
    '/answer',      'CtrlAnswer',
    '/qnstat',      'CtrlQnStat',
    '/template',    'CtrlTemplate',
    '/myaire',      'CtrlGetMyaire',
    '/partin',      'CtrlGetPartin',
    '/award',       'CtrlGetAward',
    '/topic',       'CtrlTopic',
    '/newfromtp',   'CtrlCreateQsByTmpl',
    '/getqnmsg',    'CtrlGetQnMessage',
    '/exportans',   'CtrlExportAnswer',
)

app_urls = web.application(urls, locals())

########################################
class UtilProvinceCity:
    def GET(self):
        '''获取指定省份的城市'''
        param = web.input(p='')
        if param.p:
            retval = ["不限"] + province_city.get(param.p,[])
            return formatting.json_string(retval,ensure_ascii=False)
        else:
            return '["不限"]'

########################################
class CtrlMine:
    def POST(self):
        '''个人信息设置'''
        param = web.input(r='',fsid='', in_age=None, in_marriage=None, in_academic=None, in_income=None, in_sex=None, PROVINCE=None, CITY=None)
        if cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            retval = mdb.set_fans_baseinfo(param['fsid'], param.in_age, param.in_marriage, param.in_academic, param.in_income, param.in_sex, param.PROVINCE, param.CITY)
            return retval
        else:
            return '页面已无效，请返回重新操作。'

class CtrlCreateQsnaire:
    def POST(self):
        '''通用的保存问卷基本信息'''
        param = web.input(r='',fsid='',qnid='')
        param['QN_PUBLIC'] = 1 if param.has_key('QN_PUBLIC') else 0 #包含说明选中公开结果
        param['QN_DEPLOY'] = 1 if param.has_key('QN_DEPLOY') else 0 #包含说明选中公开调查
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        param.QN_SUMMARY = formatting.replaceEmoji(param.QN_SUMMARY) #替换掉Emoji字符
        return formatting.json_string(mdb.set_naire(fsid,qnid,param))
    def PUT(self):
        '''通用的问卷创建后选择发布为指定类型的问卷，当发布为普通问卷时，直接开始回收'''
        param = web.input(r='',fsid='',qnid='',qntype=-1)
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        return formatting.json_string(mdb.set_qntype(param.fsid,param.qnid,param.qntype))

class CtrlModifyQsnaire:
    def POST(self):
        '''用于通用的问卷创建后设置各类问卷的相关信息（奖品信息/红包信息/调查币信息）'''
        param = web.input(r='',fsid='',qnid='',IMG3=[])
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        return formatting.json_string(mdb.modi_naire(qnid,param))

class CtrlNoPay:
    def POST(self):
        '''保存普通问卷'''
        param = web.input(r='',fsid='',qnid='',QN_TITLE='',QN_SUMMARY='')
        param['QN_PUBLIC'] = 1 if param.has_key('QN_PUBLIC') else 0 #包含说明选中公开结果
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        param.QN_SUMMARY = formatting.replaceEmoji(param.QN_SUMMARY) #替换掉Emoji字符
        return formatting.json_string(mdb.set_nopay(fsid,qnid,param))
    def DELETE(self):
        '''删除问卷。所有类型问卷共用接口。'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        retval = mdb.del_qsnaire(param['fsid'],param['qnid'])
        return formatting.json_string(retval)

class CtrlPaid:
    def POST(self):
        '''保存有奖问卷'''
        param = web.input(r='',fsid='',qnid='',QN_TITLE='',QN_SUMMARY='',QN_MIN=0,QN_MAX=0,QN_SEX='',QN_AGE='',QN_MARRIAGE='',QN_ACADEMIC='',PRIZE_TITLE='',PRIZE_VALUE='',IMG1='',IMG2='',IMG3=[])
        param['QN_DEPLOY'] = 0 if param.has_key('QN_DEPLOY') else 1 #包含说明选中自行分发问卷
        param['PRIZE_SEND'] = 1 if param.has_key('PRIZE_SEND') else 0 #包含说明选中自行寄送奖品
        param['QN_PUBLIC'] = 1 if param.has_key('QN_PUBLIC') else 0 #包含说明选中
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        if not param['PRIZE_VALUE']:
            return '{"error":"请输入奖品价值"}'
        if param['PRIZE_VALUE'] and not str(param['PRIZE_VALUE']).isdigit():
            return '{"error":"请输入奖品价值"}'
        param['PRIZE_VALUE'] = int(param['PRIZE_VALUE'])
        if param['PRIZE_VALUE']<=0:
            return '{"error":"奖品价值必须大于0元"}'
        param.pop('r')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        param.QN_SUMMARY = formatting.replaceEmoji(param.QN_SUMMARY) #替换掉Emoji字符
        return formatting.json_string(mdb.set_paid(fsid,qnid,param))

class CtrlHong:
    def POST(self):
        '''保存红包问卷'''
        param = web.input(r='',fsid='',qnid='',QN_TITLE='',QN_SUMMARY='')
        param['QN_PUBLIC'] = 1 if param.has_key('QN_PUBLIC') else 0 #包含说明选中
        param['QN_DEPLOY'] = 1 if param.has_key('QN_DEPLOY') else 0 #包含说明选中公开调查
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        if not param['PRIZE_VALUE']:
            return '{"error":"请输入红包金额"}'
        if param['PRIZE_VALUE'] and not str(param['PRIZE_VALUE']).isdigit():
            return '{"error":"请输入红包金额"}'
        param['PRIZE_VALUE'] = int(param['PRIZE_VALUE'])
        if param['PRIZE_VALUE']<=0:
            return '{"error":"红包金额必须大于0元"}'
        if not param['HONGBAO_NUM']:
            return '{"error":"请输入红包个数"}'
        if param['HONGBAO_NUM'] and not str(param['HONGBAO_NUM']).isdigit():
            return '{"error":"请输入红包个数"}'
        param['HONGBAO_NUM'] = int(param['HONGBAO_NUM'])
        if param['HONGBAO_NUM']<=0:
            return '{"error":"红包个数必须大于0个"}'
        if float(param['PRIZE_VALUE'])/float(param['HONGBAO_NUM'])<0.02:
            return '{"error":"红包金额太小了，请适当增加红包金额或减少红包个数"}'
        param.pop('r')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        param.QN_SUMMARY = formatting.replaceEmoji(param.QN_SUMMARY) #替换掉Emoji字符
        return formatting.json_string(mdb.set_hong(fsid,qnid,param))

class CtrlPrepay:
    def POST(self):
        '''为需要付款的问卷调用微信统一支付接口生成预支付订单，得到订单号'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        retval = mdb.call_wxpay_order(param['qnid'], web.ctx.ip)
        return formatting.json_string(retval,ensure_ascii=False)

class CtrlImage:
    def GET(self,imgid):
        '''获取图片数据'''
        #图片存储在磁盘上时，实际上是不用这个url返回图片的
        retval = mdb.get_image(imgid)
        ctype = retval[5:retval.find(';')]
        ext = ctype[ctype.find('/')+1:]
        retval = formatting.base64decode(retval[retval.find('base64,')+7:])
        web.header("Content-Type", ctype)
        web.header('Content-disposition', 'attachment;filename=%s.%s'%(imgid,ext))
        web.header("Content-Length", str(len(retval)))
        return retval

class CtrlQuestion:
    def GET(self):
        '''获取问卷题目'''
        param = web.input(qnid='')
        retval = mdb.list_question(param.qnid)
        return formatting.json_string(retval,ensure_ascii=False)
    def POST(self):
        '''保存问卷题目'''
        param = web.input(r='',fsid='',qnid='',allitem='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已超时，请返回重新进入编辑。你可以在【我发布的问卷】中找到正在编辑的问卷"}'
        param.allitem = formatting.replaceEmoji(param.allitem)
        return formatting.json_string(mdb.set_question(param['fsid'],param['qnid'], param.allitem))

class CtrlDeploy:
    def POST(self):
        '''发布问卷，开始回收。发布后问卷不能修改'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        QNOBJ = mdb.get_naire(param['qnid'])
        if not QNOBJ:
            return formatting.json_string({'error':'问卷不存在！'})
        retval = mdb.deploy_qs(QNOBJ)
        return formatting.json_string(retval)
    def DELETE(self):
        '''暂停回收。所有类型问卷共用接口。'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        retval = mdb.pause_qs(param['qnid'])
        return formatting.json_string(retval)
    def PUT(self):
        '''恢复回收。所有类型问卷共用接口。'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        retval = mdb.resume_qs(param['qnid'])
        return formatting.json_string(retval)
class CtrlStop:
    def POST(self):
        '''停止回收问卷'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        retval = mdb.stop_qs(param['qnid'])
        return formatting.json_string(retval)

class CtrlAnswer:
    def POST(self):
        '''回答问卷提交'''
        param = web.input(r='',fsid='',qnid='',AN_CONTENT='')
        if not cacher_random_checker.chkRandomValueWithPop(param['fsid'],param['r']):
            return get_render(view_render,'error')('页面已无效，请返回重新操作。')
        param['AN_CONTENT'] = formatting.replaceEmoji(param['AN_CONTENT'])
        retval = mdb.set_answer(param['qnid'],param['fsid'],param['AN_CONTENT'],web.ctx.ip)
        pagedata = {}
        pagedata['QNOBJ'] = mdb.get_naire(param['qnid'])
        mqsnaire.injectAD(pagedata) #向答卷完成后的提示页面注入广告
        if retval.has_key('success'):
            # if retval.has_key('seeurl'):
            #     return web.seeother(retval['seeurl'],True)
            # else:
            pagedata['APPID'] = wxaccount.APPID
            from models import mforweixin
            pagedata['signPackage'] = web.Storage(mforweixin.calc_jsapi_signature(web.ctx.homedomain+web.ctx.env['REQUEST_URI']))
            return get_render(view_render,'success')('提交成功',retval['success'],pagedata)
        else:
            return get_render(view_render,'error')(retval['error'],pagedata)

class CtrlQnStat:
    def GET(self):
        '''获取问卷统计结果'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return "{}"
        retval = mdb.stat_qsnaire(param.qnid)
        return formatting.json_string(retval)

class CtrlTemplate:
    def GET(self):
        '''获取模板问卷及其题目'''
        param = web.input(fsid='')
        if not param.fsid:
            retval = mdb.list_template()
        else:
            retval = mdb.list_mytmpl(param.fsid)
        return formatting.json_string(retval)
    def POST(self):
        '''从模板/历史问卷/用户题库选择题目后添加到指定问卷'''
        param = web.input(r='',fsid='',qnid='',addqis='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        return formatting.json_string(mdb.add_question(param['qnid'], param.addqis))

#取归档问卷原则：取当前年份的话从主归档表中查，取历史年份的话从对应年份归档表中查
class CtrlGetMyaire:
    def GET(self):
        '''取用户发布的问卷(归档)'''
        param = web.input(fsid='',r='',y='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return "[]"
        if not param.y:
            from datetime import datetime
            param.y = str(datetime.now().year)
        retval = mdb.list_his_myaire(param['fsid'],param.y)
        if retval==None:
            return None
        else:
            return formatting.json_string(retval)

class CtrlGetPartin:
    def GET(self):
        '''取参与过的问卷(归档)'''
        param = web.input(fsid='',r='',y='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return "[]"
        if not param.y:
            from datetime import datetime
            param.y = str(datetime.now().year)
        retval = mdb.list_his_partin(param['fsid'],param.y)
        if retval==None:
            return None
        else:
            return formatting.json_string(retval)

class CtrlGetAward:
    def GET(self):
        '''取参与过的问卷(归档)'''
        param = web.input(fsid='',r='',y='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return "[]"
        if not param.y:
            from datetime import datetime
            param.y = str(datetime.now().year)
        retval = mdb.list_his_award(param['fsid'],param.y)
        if retval==None:
            return None
        else:
            return formatting.json_string(retval)
    def POST(self):
        '''中奖用户设置通信地址和电话'''
        param = web.input(r='',fsid='',qnid='',anid='',adr='',phn='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        return formatting.json_string(mdb.set_address(param['qnid'], param['anid'],param['adr'],param['phn']))
    def PUT(self):
        '''问卷发布人设置问卷为已兑奖状态（如果是发布人就设置为1，如果是中奖人就设置为2）'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        QNOBJ = mdb.get_naire(param['qnid'])
        if param['fsid']==str(QNOBJ.FS_ID) and QNOBJ.WIN_END==0: #发布人标记为已兑奖
            return formatting.json_string(mdb.set_qsend(param['qnid'],None,1,param.get('expno')))
        elif param['fsid']==str(QNOBJ.WIN_FSID): #中奖人标记为已领奖
            return formatting.json_string(mdb.set_qsend(param['qnid'],None,2))
        else:
            return '{"error":"无效请求！"}'

class CtrlTopic:
    def POST(self):
        '''创建话题问卷'''
        #第1步，根据模板问卷，输入必要信息
        param = web.input(r='',fsid='',qnid='',tpid='',QN_TITLE='',QN_SUMMARY='',PRIZE_VALUE=0,HONGBAO_NUM=0)
        param['QN_PUBLIC'] = 1 if param.has_key('QN_PUBLIC') else 0 #包含说明选中
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        if param.has_key('sw_hongbao'):
            if not param['PRIZE_VALUE']:
                return '{"error":"请输入红包金额"}'
            if param['PRIZE_VALUE'] and not str(param['PRIZE_VALUE']).isdigit():
                return '{"error":"请输入红包金额"}'
            param['PRIZE_VALUE'] = int(param['PRIZE_VALUE'])
            if param['PRIZE_VALUE']<=0:
                return '{"error":"红包金额必须大于0元"}'
            if not param['HONGBAO_NUM']:
                return '{"error":"请输入红包个数"}'
            if param['HONGBAO_NUM'] and not str(param['HONGBAO_NUM']).isdigit():
                return '{"error":"请输入红包个数"}'
            param['HONGBAO_NUM'] = int(param['HONGBAO_NUM'])
            if param['HONGBAO_NUM']<=0:
                return '{"error":"红包个数必须大于0个"}'
            if float(param['PRIZE_VALUE'])/float(param['HONGBAO_NUM'])<0.02:
                return '{"error":"红包金额太小了，请适当增加红包金额或减少红包个数"}'
        else:
            param['PRIZE_VALUE'] = 0
            param['HONGBAO_NUM'] = 0
        param.pop('r')
        param.pop('sw_hongbao','')
        fsid = param.pop('fsid')
        qnid = param.pop('qnid')
        tpid = param.pop('tpid')
        refqn = param.pop('refqn')
        param['client_ip'] = web.ctx.ip
        param.QN_SUMMARY = formatting.replaceEmoji(param.QN_SUMMARY) #替换掉Emoji字符
        return formatting.json_string(mdb.set_topic(fsid,tpid,qnid,refqn,param))

class CtrlCreateQsByTmpl:
    def POST(self):
        '''复刻指定模板创建新问卷'''
        param = web.input(r='',fsid='',tpid='',qntype='',allitem='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        fsid = param.pop('fsid')
        tpid = param.pop('tpid')
        qntype = param.pop('qntype')
        if qntype not in (0,1,2,3,'0','1','2','3'):
            qntype = -1
        allitem = param.pop('allitem')
        refqn = param.pop('refqn','')
        return formatting.json_string(mdb.create_qs(fsid,tpid,qntype,allitem,refqn))

class CtrlGetQnMessage:
    def GET(self):
        '''获取问卷消息'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        QNOBJ = mdb.get_naire(param.qnid)
        if not QNOBJ:
            return '{"error":"问卷不存在！"}'
        FSOBJ = mdb.get_fans_byfsid(QNOBJ.FS_ID)
        mqsnaire.delaySendMessage(FSOBJ.OPENID, mqsnaire.getQsArticleBody(QNOBJ))
        txtmsg = '直接戳链接：%s。'%(QNOBJ.SHARE_LINK.encode('utf8'))
        txtmsg = txtmsg+'或者关注【问卷调查大师】公众号，发文字消息【%s】（可输入部分文字模糊搜索）得到问卷参与链接。'%(QNOBJ.QN_TITLE.encode('utf8'))
        if QNOBJ.QN_TYPE==3:
            txtmsg = txtmsg+'填写问卷可获答谢%d调查币，'%int(round(QNOBJ.HONGBAO_MNY,0))
        txtmsg = txtmsg+'可获奖励基数%d调查币。'%(QNOBJ.QN_NO)
        mqsnaire.delaySendMessage(FSOBJ.OPENID, txtmsg, 500)
        return '{"success":"问卷消息已发送，您可以分享出去以便推广问卷。若您没有收到，可能是因为您与服务号的交互时间超过了48小时，请回到会话界面点击任意菜单再来点我！"}'

class CtrlExportAnswer:
    def GET(self):
        '''将问卷答卷导出到excel文件'''
        param = web.input(r='',fsid='',qnid='')
        if not cacher_random_checker.chkRandomValueNotPop(param['fsid'],param['r']):
            return '{"error":"页面已无效，请返回重新操作。"}'
        param.pop('r')
        QNOBJ = mdb.get_naire(param.qnid)
        if not QNOBJ:
            return get_render(view_render,'error')('问卷不存在！',{},False)
        if not QNOBJ.NUM_VOTE:
            return get_render(view_render,'error')('问卷还没有回收答卷！',{},False)
        retval = mdb.export_answer_excel(param.qnid)
        web.header("Content-Type", "application/octet-stream; charset=UTF-8")
        web.header("Content-Length", str(len(retval)))
        web.header("Content-Disposition",'attachment;filename="%s.xls"'%QNOBJ.QN_TITLE.encode('utf8'))
        return retval

