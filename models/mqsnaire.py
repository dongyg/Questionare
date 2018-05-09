#!/usr/bin/env python
#-*- encoding: utf-8 -*-

#【问卷调查大师】公众号的与用户交互方面的功能。treatReciveMessage为处理微信事件响应函数，针对各类事件调用相应的处理函数

from config import *

import mdb, mforweixin


################################################################################
def pushTask(fn,args,ms=50):
    '''创建延时任务'''
    from helpers import TaskScheduler
    delta = datetime.timedelta(milliseconds=ms)
    now = datetime.datetime.now()
    if not isinstance(args,tuple):
        args = (args,)
    TaskScheduler.add_task(fn, args, start_time=now+delta)
def delaySendMessage(openid,send_msg,ms=50):
    '''延时发送消息给粉丝。ms延时毫秒数，默认50毫秒'''
    #直接向粉丝操作回复消息时，发现图文消息picurl为空的话会显示个空白，但客服消息不会，因此用延时发客服消息的办法发送消息。
    #另外，回复消息需要在5秒内，否则微信服务器认为超时。微信服务器也建议先回复success，然后再发送消息。也要用延时发送的方法
    if send_msg:
        args = (openid, send_msg)
        if isinstance(send_msg, list) or isinstance(send_msg, dict): # 图文articles
            fn = mforweixin.sendLinkRTMessage
        else:
            fn = mforweixin.sendTextMessage
        pushTask(fn,args,ms)

################################################################################
#处理用户事件和消息
def treatReciveMessage(xml_body):
    """处理接收到的微信事件和消息，返回回复消息"""
    json_data = mforweixin.toJson(xml_body)
    fromuser = json_data.get('FromUserName')
    touser = json_data.get('ToUserName')
    content = json_data.get('Content')
    msgtype = json_data.get('MsgType')
    event = json_data.get('Event' or None)
    #将收到的消息保存到日志表
    if web.config.sysenv_debug:
        mforweixin.set_logs(fromuser, touser, json_data.get('CreateTime',int(time.time())), msgtype,event,json_data.get('EventKey'),content,json_data.get('MsgId'),json_data.get('MediaId'))
    reply_msg = ''
    if msgtype == 'event':
        #关注事件
        if event == 'subscribe':
            delaySendMessage(fromuser, MSG_WELCOME)
            #扫描带参数二维码事件，用户未关注时，进行关注后的事件推送
            inby = 10000
            if json_data.get('EventKey','').startswith('qrscene_'):
                # print json_data['EventKey'] #事件KEY值，qrscene_为前缀，后面为二维码的参数值
                # print json_data['Ticket']   #二维码的ticket，可用来换取二维码图片
                scene_id = json_data['EventKey'].replace('qrscene_','')
                if scene_id<100000: #小于10万的是固定二维码，即是营销人员，取营销人员的FSID作为INBY
                    inby = mdb.get_fsid_by_sceneid(scene_id)
                else:
                    QNOBJ = mdb.get_naire_byqr(scene_id)
                    #有奖问卷或红包问卷发布人才能成为别人的引荐人，或问卷发布人是系统配置的营销人员
                    import madmin
                    inby = QNOBJ.FS_ID if QNOBJ and (QNOBJ.QN_TYPE in (1,2) or QNOBJ.FS_ID in madmin.get_salers()) else inby
                    if QNOBJ:
                        delaySendMessage(fromuser, replyScan(scene_id), 2000)
            mforweixin.set_weixinfan(fromuser,{'SUBSCRIBE':1,'IN_BY':inby})
            replySubscribe(fromuser) #新粉丝关注时发所设置的消息
            replayQnaire(fromuser) #新粉丝关注时发所设置的问卷
            pushTask(mforweixin.get_fansinfo, fromuser) #获取微信用户信息
        #取消关注事件
        elif event == 'unsubscribe':
            mforweixin.set_weixinfan(fromuser,{'SUBSCRIBE':0})
        #点击菜单跳转链接时的事件推送
        elif event == 'VIEW':
            # print json_data['EventKey']
            pass
        #点击菜单拉取消息时的事件推送
        elif event == 'CLICK':
            # print json_data['EventKey']
            mforweixin.set_weixinfan(fromuser)
            if json_data['EventKey']=='M10':   #答有奖问卷
                delaySendMessage(fromuser, replyClick10(fromuser))
            elif json_data['EventKey']=='M11': #答红包问卷
                delaySendMessage(fromuser, replyClick11(fromuser))
            elif json_data['EventKey']=='M12': #我答过的问卷
                delaySendMessage(fromuser, replyClick12(fromuser))
            elif json_data['EventKey']=='M13': #中奖和红包记录
                delaySendMessage(fromuser, replyClick13(fromuser))
            elif json_data['EventKey']=='M20': #创建有奖问卷
                delaySendMessage(fromuser, replyClick20(fromuser))
            elif json_data['EventKey']=='M21': #创建红包问卷
                delaySendMessage(fromuser, replyClick21(fromuser))
            elif json_data['EventKey']=='M22': #创建普通问卷
                delaySendMessage(fromuser, replyClick22(fromuser))
            elif json_data['EventKey']=='M23': #我发布的问卷
                delaySendMessage(fromuser, replyClick23(fromuser))
            elif json_data['EventKey']=='M31': #我的信息
                delaySendMessage(fromuser, replyClick31(fromuser))
            elif json_data['EventKey']=='MA1': #答互助问卷
                delaySendMessage(fromuser, replyClickMA1(fromuser))
            elif json_data['EventKey']=='MB3': #从模板创建问卷
                delaySendMessage(fromuser, replyClickMB3(fromuser))
            elif json_data['EventKey']=='MB4': #创建空白问卷
                delaySendMessage(fromuser, replyClickMB4(fromuser))
            elif json_data['EventKey']=='MC1': #签到
                delaySendMessage(fromuser, replyClickMC1(fromuser))
            elif json_data['EventKey']=='MC2': #我的调查币
                delaySendMessage(fromuser, replyClickMC2(fromuser))
        #扫描带参数二维码事件，用户已关注时的事件推送
        elif event == 'SCAN':
            # print json_data['EventKey'] #事件KEY值，是一个32位无符号整数，即创建二维码时的二维码scene_id
            # print json_data['Ticket']   #二维码的ticket，可用来换取二维码图片
            mforweixin.set_weixinfan(fromuser)
            delaySendMessage(fromuser, replyScan(json_data['EventKey']))
        #上报地理位置事件
        elif event == 'LOCATION':
            # print json_data['Latitude']  #地理位置纬度
            # print json_data['Longitude'] #地理位置经度
            # print json_data['Precision'] #地理位置精度
            pass
    elif msgtype == 'text':
        mforweixin.set_weixinfan(fromuser)
        reply_msg = replyTextMessage(fromuser,content)
    #如果有消息需要回复，在接收消息的时候直接回复
    if reply_msg:
        if isinstance(reply_msg, list) or isinstance(reply_msg, dict): # 图文articles
            if isinstance(reply_msg, list):
                return mforweixin.replyArticle(wxaccount.ORIGINAL_ID, fromuser, reply_msg)
            else:
                return mforweixin.replyArticle(wxaccount.ORIGINAL_ID, fromuser, [reply_msg])
        elif reply_msg.startswith('<xml>'):
            return reply_msg
        else:
            return mforweixin.replyText(wxaccount.ORIGINAL_ID, fromuser, reply_msg)
    else:
        return 'success'

def treatWxpayNotify(xml_body):
    '''处理微信支付通知'''
    retdat = mforweixin.checkWxpayNotify(xml_body)
    if retdat.has_key('success'):
        return mdb.set_wxpay_resp(retdat['success'])
    else:
        return retdat

def execSendHongbao(openid,amount,billno,clientip,actname='',wishing='',remark=''):
    if not actname:
        actname = '红包问卷-抢红包'
    if not wishing:
        wishing = '感谢参与红包问卷，小小红包请笑纳！'
    if not remark:
        remark = '来问卷调查大师参与问卷调查，抢红包，抽大奖'
    retval = ''
    retdat = mforweixin.sendHongbao(openid,amount,billno,actname,wishing,remark,clientip)
    if retdat.has_key('success'):
        retval = mdb.set_wxpay_hong(retdat['success'])
    else:
        retval = retdat
    if retval.has_key('error'): #有错误时记录。因为这个是异步执行的，没有等待返回，有错误时记录下来以便查阅
        mforweixin.set_logs('ERROR','RED',content=formatting.json_string(retval))
    mforweixin.set_logs('DEBUG','RED',content=(openid+' - '+str(amount)+' - '+billno))
    return retval

def sendredpack(openid,amount,billno):
    '''发红包'''
    #VARIANT:ip地址是运行系统的电脑ip地址(对外网)
    #PS:实测发现，所传ip并不是我电脑的外网ip发红包也能成功，貌似只要这个ip在商户的API安全中配置了就可以
    pushTask(execSendHongbao,(openid,amount,billno,'115.159.28.254'))

def getStateBusinessID(state):
    '''根据微信网页授权的url中的state参数获取业务数据ID。这里state是qnid，返回问卷的fsid'''
    #这个函数被mforweixin调用
    QNOBJ = mdb.get_naire(state)
    #有奖问卷或红包问卷发布人才能成为别人的引荐人，或问卷发布人是系统配置的营销人员
    import madmin
    return QNOBJ.FS_ID if QNOBJ and (QNOBJ.QN_TYPE in (1,2) or QNOBJ.FS_ID in madmin.get_salers()) else 10000

################################################################################
#菜单/扫码/消息等响应
def getQsArticleBody(QNOBJ,index=0,packauth=True):
    '''为问卷对象生成news图文消息格式。有奖问卷或红包问卷。index=0使用大图，否则使用小图'''
    if not QNOBJ: return ''
    retval = {"title":QNOBJ.SHARE_TITLE,"url":QNOBJ.SHARE_LINK,"description":QNOBJ.SHARE_DESC,"picurl":QNOBJ.SHARE_PICURL}
    if index==0:
        retval['picurl'] = '%s'%(QNOBJ.IMG1_URL) if QNOBJ.get('IMG1_URL') else retval['picurl']
    #图文消息url用微信网页授权封装
    if packauth:
        retval['url'] = mforweixin.get_mp_authurl("%s/link"%(HOST_NOS),QNOBJ.QN_ID)
    else:
        retval['url'] = "%s/link?state=%s"%(HOST_NOS,QNOBJ.QN_ID)
    return retval
def getTopicArticleBody(TPOBJ):
    '''为话题问卷生成参与链接'''
    if not TPOBJ: return ''
    retval = {"title":TPOBJ.SHARE_TITLE,"url":'',"description":TPOBJ.SHARE_DESC,"picurl":''}
    if TPOBJ.get('IMG1_URL'):
        retval['picurl'] = '%s'%(TPOBJ.IMG1_URL)
    elif TPOBJ.get('SHARE_PICURL'):
        retval['picurl'] = '%s'%(TPOBJ.SHARE_PICURL)
    retval['url'] = mforweixin.get_mp_authurl("%s/newfromtp"%(HOST_NOS),TPOBJ.QN_ID)
    return retval

def replyClick10(fromuser):
    '''我要答卷：有奖问卷'''
    # 答卷前，判断是否新用户。新用户需要完善个人信息。否则，回复若干条图文消息。取若干个非推送的、用户基本信息符合筛选条件的问卷。
    retval = ''
    FSOBJ = mdb.get_fans_byopenid(fromuser)
    if FSOBJ:
        cacher_random_checker.popRandomValueForFSID(FSOBJ.FS_ID)
    #如果年龄为空，说明是新用户，返回图文消息，提示用户需要填写个人信息后再参与问卷
    if FSOBJ and not FSOBJ.P2_AGE:
        pushTask(mforweixin.get_fansinfo, fromuser) #获取微信用户信息
        retval = {"title":"完善资料", "url":mforweixin.get_mp_authurl("%s/p31"%(HOST_NOS)), "description":"参与问卷前请先完善资料，所填写资料只用于调查问卷统计，不涉及隐私内容。"}
        return retval
    if FSOBJ:
        retval = mdb.list_cananswer(FSOBJ.FS_ID,1)
        #问卷参与url：用微信网页授权并跳转
        retval = [getQsArticleBody(x,i) for i,x in enumerate(retval)]
        retval = [x for x in retval if x]
        if retval:
            return retval
    return '没有更多有奖问卷了！'

def replyClick11(fromuser):
    '''我要答卷：红包问卷'''
    # 答卷前，判断是否新用户。新用户需要完善个人信息。否则，回复若干条图文消息。取若干个非推送的、用户基本信息符合筛选条件的问卷。
    retval = ''
    FSOBJ = mdb.get_fans_byopenid(fromuser)
    if FSOBJ:
        cacher_random_checker.popRandomValueForFSID(FSOBJ.FS_ID)
    #如果年龄为空，说明是新用户，返回图文消息，提示用户需要填写个人信息后再参与问卷
    if FSOBJ and not FSOBJ.P2_AGE:
        pushTask(mforweixin.get_fansinfo, fromuser) #获取微信用户信息
        retval = {"title":"完善资料", "url":mforweixin.get_mp_authurl("%s/p31"%(HOST_NOS)), "description":"参与问卷前请先完善资料，所填写资料只用于调查问卷统计，不涉及隐私内容。"}
        return retval
    if FSOBJ:
        retval = mdb.list_cananswer(FSOBJ.FS_ID,2)
        #问卷参与url：用微信网页授权并跳转
        retval = [getQsArticleBody(x,i) for i,x in enumerate(retval)]
        retval = [x for x in retval if x]
        if retval:
            return retval
    return '没有更多红包问卷了！'

def replyClickMA1(fromuser):
    '''答互助问卷'''
    retval = ''
    FSOBJ = mdb.get_fans_byopenid(fromuser)
    if FSOBJ:
        cacher_random_checker.popRandomValueForFSID(FSOBJ.FS_ID)
    #如果年龄为空，说明是新用户，返回图文消息，提示用户需要填写个人信息后再参与问卷
    if FSOBJ and not FSOBJ.P2_AGE:
        pushTask(mforweixin.get_fansinfo, fromuser) #获取微信用户信息
        retval = {"title":"完善资料", "url":mforweixin.get_mp_authurl("%s/p31"%(HOST_NOS)), "description":"参与问卷前请先完善资料，所填写资料只用于调查问卷统计，不涉及隐私内容。"}
        return retval
    if FSOBJ:
        retval = mdb.list_cananswer(FSOBJ.FS_ID,3)
        #问卷参与url：用微信网页授权并跳转
        retval = [getQsArticleBody(x,i) for i,x in enumerate(retval)]
        retval = [x for x in retval if x]
        if retval:
            return retval
    return '没有更多互助问卷了！'

def replyClick12(fromuser):
    '''已答问卷'''
    # 回复一条图文消息。包含用户已答问卷的统计结果。点击图文消息进入用户自己的已答问卷浏览页面，查看已答过的问卷，参与时间，获得的参与号，等等。进而可看问卷基本信息，结果。
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    cacher_random_checker.popRandomValueForFSID(fsid)
    c0,c1,c2,c3 = mdb.count_answer(fsid)
    if c0==0 and c1==0 and c2==0 and c3==0:
        return '您还没参与过任何调查问卷。'
    else:
        retval = {"title":"已答问卷", "url":mforweixin.get_mp_authurl("%s/p12"%(HOST_NOS)), "description":"您参与过%d个普通问卷，%d个有奖问卷，%d个红包问卷，%d个互助问卷\n\n点击查看详情"%(c0,c1,c2,c3)}
    return retval

def replyClick13(fromuser):
    '''馅饼砸中，中奖和红包记录'''
    # 若用户未中过奖，回复一条文本消息。若已中过奖，回复一条图文消息，点击进入查看中奖详细情况：中奖清单，参与的是哪个问卷，其参与号汇总情况，摇号结果，等等。
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    cacher_random_checker.popRandomValueForFSID(fsid)
    count,hongbao = mdb.count_award(fsid)
    if count==0 and hongbao==0:
        return '您还没有中过奖，而且居然红包也没抢到过！'
    else:
        needsend, detail = mdb.get_hongbao_cache(fsid)
        retval = {"title":"中奖与红包记录", "url":mforweixin.get_mp_authurl("%s/p13"%(HOST_NOS)), "description":"您中过 %d 次奖，获得红包总金额 %.2f 元%s。点击查看详情"%(count,hongbao,('，等待发放 %.2f 元，累计达到1元时会自动发放'%needsend if needsend>0 else ''))}
    return retval

def replyClick20(fromuser):
    '''创建有奖问卷'''
    # 回复外链图文消息。用户点击图文消息打开创建有奖问卷页面，图文消息的url是带用户ID参数的
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    retmsg,count = mdb.get_nocomplete(fsid,[1]) #先检查该用户是否有未完成的有奖问卷，有就提示他
    delaySendMessage(fromuser, retmsg)
    cacher_random_checker.popRandomValueForFSID(fsid)
    limit = int(web.config.app_configuration.get('sys:limit_1',10))
    if count<limit:
        count = mdb.count_today_aire(fsid)[1]
        if count>=limit:
            return '您今天已经创建了%d个有奖问卷，请明天再来。'%limit
        else:
            retval = {"title":"创建有奖问卷", "url":mforweixin.get_mp_authurl("%s/paid1"%(HOST_NOS)), "description":"您今天创建了%d个有奖问卷，还可以创建%d个\n\n点击去创建"%(count,limit-count)}
        return retval

def replyClick21(fromuser):
    '''创建红包问卷'''
    # 回复外链图文消息。用户点击图文消息打开创建有奖问卷页面，图文消息的url是带用户ID参数的
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    retmsg,count = mdb.get_nocomplete(fsid,[2]) #先检查该用户是否有未完成的有奖问卷，有就提示他
    delaySendMessage(fromuser, retmsg)
    cacher_random_checker.popRandomValueForFSID(fsid)
    limit = int(web.config.app_configuration.get('sys:limit_2',10))
    if count<limit:
        count = mdb.count_today_aire(fsid)[2]
        if count>=limit:
            return '您今天已经创建了%d个红包问卷，请明天再来。'%limit
        else:
            retval = {"title":"创建红包问卷", "url":mforweixin.get_mp_authurl("%s/hong1"%(HOST_NOS)), "description":"您今天创建了%d个红包问卷，还可以创建%d个\n\n点击去创建"%(count,limit-count)}
        return retval

def replyClick22(fromuser):
    '''创建普通问卷'''
    # 判断用户今日是否可创建普通问卷，如不可创建，回复文本消息提示今天已创建过。若可创建，回复外链图文消息。用户点击图文消息打开创建普通问卷页面，图文消息的url是带用户ID参数的
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    retmsg,count = mdb.get_nocomplete(fsid,[0]) #先检查该用户是否有未完成的有奖问卷，有就提示他
    delaySendMessage(fromuser, retmsg)
    cacher_random_checker.popRandomValueForFSID(fsid)
    limit = int(web.config.app_configuration.get('sys:limit_0',2))
    if count<limit:
        count = mdb.count_today_aire(fsid)[0]
        if count>=limit:
            return '您今天已经创建了%d个普通问卷，请明天再来。'%limit
        else:
            retval = {"title":"创建普通问卷", "url":mforweixin.get_mp_authurl("%s/nopay1"%(HOST_NOS)), "description":"您今天创建了%d个普通问卷，还可以创建%d个。\n\n点击去创建"%(count,limit-count),"picUrl":""}
        return retval

def replyClick23(fromuser):
    '''我发布的问卷'''
    # 若用户未发布过任何问卷，回复一条文本消息。
    # 若用户已发布过问卷，回复一条图文消息，包含所发问卷的统计结果。点击进入我发布的问卷查看页面，列表清单查阅所发布的所有问卷，每个问卷可进入问卷查看页面，除了像答卷人可看到的问卷详情外，还可查看状态、统计结果、奖品发放情况等等。
    # 选择自己寄送奖品的，在寄送奖品后，通过这里，可登记快递信息、可申请退保证金，等等。
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    cacher_random_checker.popRandomValueForFSID(fsid)
    retmsg,count = mdb.get_nocomplete(fsid,[-1,0,1,2,3])
    c0,c1,c2,c3 = mdb.count_aire(fsid)
    if c0==0 and c1==0 and c2==0 and c3==0 and count==0:
        return '您还没发布过问卷。'
    else:
        retval = {"title":"我发布的问卷", "url":mforweixin.get_mp_authurl("%s/p23"%(HOST_NOS)), "description":"您发布过%d个普通问卷，%d个有奖问卷，%d个红包问卷，%d个互助问卷。有%d个正在编辑的问卷\n\n点击查看详情"%(c0,c1,c2,c3,count)}
    return retval

def replyClick31(fromuser):
    '''我的信息'''
    # 回复一个图文消息，显示用户的统计信息：发了多少个问卷、答了多少个问卷、中奖几次，引荐了多少粉丝，个人基本信息。提示点击可修改个人信息。
    # 个人信息页面可查看自己的个人信息，可编辑。
    retval = ''
    FSOBJ = mdb.get_fans_byopenid(fromuser)
    fsid = FSOBJ.FS_ID if FSOBJ else ''
    p0, p1, p2, p3, a0, a1, a2, a3, win, suma2, f1 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  #发了多少个问卷(无偿，有偿，红包)、答了多少个问卷(无偿，有偿，红包)、中奖几次(中奖，红包)，引荐了多少粉丝
    if fsid:
        cacher_random_checker.popRandomValueForFSID(fsid)
        p0, p1, p2, p3, a0, a1, a2, a3, win, suma2, f1 = mdb.stat_fans_byfsid(fsid)
        info = '省份：%s\n城市：%s\n年龄：%s\n婚姻：%s\n学历：%s\n收入：%s'%(FSOBJ.PROVINCE.encode('utf8') if FSOBJ.PROVINCE else '',FSOBJ.CITY.encode('utf8') if FSOBJ.CITY else '',mdb.get_basetitle('AGE',FSOBJ.P2_AGE),mdb.get_basetitle('MARRIAGE',FSOBJ.P2_MARRIAGE),mdb.get_basetitle('ACADEMIC',FSOBJ.P2_ACADEMIC),mdb.get_basetitle('INCOME',FSOBJ.P2_INCOME))
        retval = {"title":"我的信息", "url":mforweixin.get_mp_authurl("%s/p31"%(HOST_NOS)), "description":"发布: 普通%d个,有奖%d个,红包%d个,互助%d个\n参与: 普通%d个,有奖%d个,红包%d个,互助%d个\n中奖次数: %d次。获得红包: %.2f元%s\n引荐粉丝: %d\n\n%s\n\n可点击修改个人信息"%(p0, p1, p2, p3, a0, a1, a2, a3, win, suma2, ('，未发%.2f'%FSOBJ.NOTPAY_A2 if FSOBJ.NOTPAY_A2 else ''), f1, info)}
        #向自己人发送随机数
        if fsid in web.config.app_configuration['run:selfman']:
            delaySendMessage(fromuser, cacher_random_checker.genRandomValueForFSID(fsid))
    return retval

def replyScan(scene_id):
    '''处理扫码。扫问卷二维码时，发送问卷参与图文消息'''
    retval = ''
    QNOBJ = mdb.get_naire_byqr(scene_id)
    retval = getQsArticleBody(QNOBJ)
    return retval

def replySubscribe(openid):
    '''关注时发的消息'''
    media_id = web.config.app_configuration.get('sys:subreply','') #设置的一个图文消息素材ID，即media_id
    if media_id:
        if wxcode=='test':
            pushTask(mforweixin.sendTextMessage, (fromuser, media_id))
        else:
            pushTask(mforweixin.sendMPNews, (openid, media_id), 2000)

def replayQnaire(fromuser):
    qnid = web.config.app_configuration.get('sys:subnaire','') #设置问卷ID在关注时返回
    if qnid:
        QNOBJ = mdb.get_naire(qnid)
        if QNOBJ and QNOBJ.QN_STATUS==2:
            FSOBJ = mdb.get_fans_byopenid(fromuser)
            ANOBJ = mdb.get_answer(QNOBJ.QN_ID,FSOBJ.FS_ID)
            if not ANOBJ: #如果没参与过才发
                msg = getQsArticleBody(QNOBJ)
                delaySendMessage(fromuser,msg,500)

def replyTextMessage(fromuser,content):
    '''解析收到的文本消息。允许管理员用户通过文字指令进行管理操作'''
    retval = ''
    content = content.encode('utf8') #收到的消息字符串是unicode类型
    fsid = mdb.get_fsid_byopenid(fromuser)
    #测试号上允许访问扒问卷星的页面
    if wxcode=='test' and fsid in web.config.app_configuration['run:selfman'] and content.find('sojump.com')>=0:
        wjid = formatting.get_sojump_id(content)
        qnid = 'sojump_'+wjid
        qnid = hashlib.md5(qnid).hexdigest()
        if mdb.get_naire(qnid):
            retval = '编号为 %s 的问卷已经有了！'%wjid
        else:
            # url = '%s/admin/bawj?fsid=%s&r=%s&wjid=%s'%(HOST_NOS,fsid,cacher_random_checker.genRandomValueForFSID(fsid),wjid)
            url = mforweixin.get_mp_authurl("%s/admin/bawj"%(HOST_NOS),wjid)
            retval = {"title":"扒问卷", "url":url, "description":"要扒问卷星的问卷吗？点我继续","picurl":""}
    #管理人员指令
    import madmin
    if not retval and fsid in madmin.get_administrators():
        if content=='?' or content=='？':
            retval = '1.当日实时答卷数\n2.预览抽奖\n3.昨日统计数据\n33.昨日结算\n4.按日统计数据的走势图\n5.营销推广管理\n6.本周答卷王\nC.从系统模板创建问卷\nD.查看调试数据'
        elif content=='1': #1.当日实时答卷数
            today = datetime.datetime.today().strftime("%Y%m%d")
            countans = web.listget(dbFrame.select("QN_ANSWERS",what="COUNT(*) CNT",vars=locals(),where="DATE_FORMAT(INPUT_TIME,'%Y%m%d')=$today").list(),0,{}).get('CNT',0)
            return '今日实时答卷数：%d'%countans
        elif content=='2': #2.预览抽奖
            pushTask(previewLottery, fromuser, 0)
        elif content=='33': #33.昨日结算\n
            pushTask(dailyWork, (fromuser,formatting.date_add(-1).strftime("%Y%m%d")), 0)
        elif content=='3': #3.昨日统计数据
            import madmin
            retval = '\n'.join(['%s: %s'%(key,val) for key, val in madmin.get_lastday_stat()])
        elif content=='4': #4.数据趋势图
            retval = {"title":"按日统计数据的走势图", "url":mforweixin.get_mp_authurl("%s/admin/chartdaily"%(HOST_NOS)), "description":"按日统计数据的走势图","picurl":""}
        elif content=='5': #5.营销推广管理
            retval = {"title":"营销推广管理", "url":mforweixin.get_mp_authurl("%s/admin/mngmarket"%(HOST_NOS)), "description":"查看营销推广数据，支付推广报酬","picurl":""}
        elif content=='6': #6.本周答卷王
            retval = []
            for idx,x in enumerate(mdb.stat_thisweek_coin(),1):
                retval.append('%d. %s  %s'%(idx,formatting.unAscSafeString(x.NICKNAME).encode('utf8'),x.CHG_AMOUNT))
            if not retval:
                retval = '无数据'
            else:
                retval = '\n'.join(retval)
        elif content.lower()=='c':
            pass
        elif content.lower()=='d': #D.查看调试数据
            retval = {"title":"查看调试数据", "url":mforweixin.get_mp_authurl("%s/debug"%(HOST_NOS)), "description":"查看调试数据。已重新加载了系统配置数据。","picurl":""}
        elif content.startswith('black'):
            fsid = content.replace('black','')
            if 'run:blacklist' not in web.config.app_configuration:
                web.config.app_configuration['run:blacklist'] = []
            if fsid:
                for x in fsid.split(','):
                    web.config.app_configuration['run:blacklist'].append(x)
            web.config.app_configuration['run:blacklist'] = list(set(web.config.app_configuration['run:blacklist']))
            retval = formatting.json_string(web.config.app_configuration['run:blacklist'])
        elif content.startswith('white'):
            fsid = content.replace('white','')
            if 'run:blacklist' not in web.config.app_configuration:
                web.config.app_configuration['run:blacklist'] = []
            if fsid:
                for x in fsid.split(','):
                    if x in web.config.app_configuration['run:blacklist']:
                        web.config.app_configuration['run:blacklist'].remove(x)
            web.config.app_configuration['run:blacklist'] = list(set(web.config.app_configuration['run:blacklist']))
            retval = formatting.json_string(web.config.app_configuration['run:blacklist'])
    else:
        retval = decodeReceiveMessage(fromuser,fsid,content)
        if retval:
            return retval
        #不能解析粉丝发来的消息，先把【发达消息】发给粉丝
        pushTask(mforweixin.sendTextMessage, (fromuser, '没有搜索到有关[%s]的问卷。客服也可能在偷懒╯﹏╰，看看下面几篇文章吧，或许对您有用'%content))
        if wxcode=='test':
            pushTask(mforweixin.sendTextMessage, (fromuser, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'),2000)
        else:
            pushTask(mforweixin.sendMPNews, (fromuser, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'),2000)
        #将粉丝发发来的消息转给我自己
        pushTask(madmin.sendToMe, ('{0}:{1}'.format(fsid,content),))
        #按要求返回特定格式数据，消息便会发到客服
        retval = mforweixin.replyCustomerService(wxaccount.ORIGINAL_ID, fromuser)
    return retval

def replyClickMB3(fromuser):
    '''从模板创建问卷'''
    tps = json.loads(web.config.app_configuration.get('sys:qstemplate','[]'))
    retval = []
    for x in tps:
        TPOBJ = mdb.get_naire(x)
        art = {"title":TPOBJ.QN_TITLE,"url":'',"description":TPOBJ.QN_SUMMARY,"picurl":''}
        if TPOBJ.get('IMG1_URL'):
            art['picurl'] = '%s'%(TPOBJ.IMG1_URL)
        elif TPOBJ.get('SHARE_PICURL'):
            art['picurl'] = '%s'%(TPOBJ.SHARE_PICURL)
        art['url'] = mforweixin.get_mp_authurl("%s/newfromtp"%(HOST_NOS),TPOBJ.QN_ID)
        retval.append(art)
    return retval

def replyClickMB4(fromuser):
    '''创建空白问卷'''
    #流程：录入问卷基本信息（标题、描述、公开结果、公开调查、目标样本数、筛选条件，640px图），录入问卷题目，预览并选择发布问卷类型（有奖/红包/互助问卷分别支付后发布，普通问卷直接发布）
    #如果用户当前未编辑完成的问卷个数超过5个，就不允许创建新的问卷，要先删除无用的问卷
    retval = ''
    fsid = mdb.get_fsid_byopenid(fromuser)
    retmsg,count = mdb.get_nocomplete(fsid,[-1,0,1,2,3]) #先检查该用户是否有未完成的问卷
    delaySendMessage(fromuser, retmsg)
    cacher_random_checker.popRandomValueForFSID(fsid)
    limit = 5
    if count<limit:
        c0,c1,c2,c3 = mdb.count_aire(fsid)
        retval = {"title":"创建问卷", "url":mforweixin.get_mp_authurl("%s/createqs"%(HOST_NOS)), "description":"您发布过%d个普通问卷，%d个有奖问卷，%d个红包问卷，%d个互助问卷，有%d个正在编辑中。\n\n点击创建新问卷"%(c0,c1,c2,c3,count),"picUrl":""}
    return retval

def replyClickMC1(fromuser):
    '''签到'''
    fsid = mdb.get_fsid_byopenid(fromuser)
    mforweixin.get_fansinfo(fromuser)
    today = datetime.datetime.today().strftime("%Y%m%d")
    retdat = mdb.set_sign(fsid,today)
    if retdat[0]>0:
        retval = '签到成功！获得%d调查币，调查币余额%d，连续签到%d天'%(retdat)
    else:
        retval = '今日已签过！连续签到%d天。调查币余额%d'%(retdat[2],retdat[1])
    return retval

def replyClickMC2(fromuser):
    '''我的调查币'''
    retval = ''
    mforweixin.get_fansinfo(fromuser)
    cacher_fsid_byopenid.delete(fromuser)
    FSOBJ = mdb.get_fans_byopenid(fromuser)
    fsid = FSOBJ.FS_ID if FSOBJ else ''
    if fsid:
        cacher_random_checker.popRandomValueForFSID(fsid)
        retval = {"title":"我的调查币", "url":mforweixin.get_mp_authurl("%s/pmc2"%(HOST_NOS)), "description":"当前调查币余额 %d\n用户等级 %s\n\n点击查看详情"%(FSOBJ.get('COIN_HOLD',0),mdb.get_fans_level(FSOBJ))}
    return retval

################################################################################
def decodeReceiveMessage(fromuser,fsid,content):
    '''解析收到的消息，给粉丝自动回复'''
    retval = ''
    if content=='话题':
        retval = [getTopicArticleBody(x) for x in mdb.list_topics()]
    elif content=='推广计划':
        import madmin
        if fsid in madmin.get_salers():
            if wxcode=='test':
                pushTask(mforweixin.sendTextMessage, (fromuser, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'))
            else:
                pushTask(mforweixin.sendMPNews, (fromuser, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'))
            retval = '您已经是推广计划成员！'
        else:
            retval = applyMarketing(fsid)
    else:
        #否则，查找问卷
        findqn = mdb.list_0find(fsid,content)
        if findqn:
            retval = [getQsArticleBody(mdb.append_naire_imgurl(x),i) for i,x in enumerate(findqn)]
        elif content.find('问卷')>=0 or content.find('调查')>=0:
            retval = '想创建问卷？请点【发问卷】菜单。想参与有奖问卷抽奖或者答问卷抢红包，请点【答问卷】菜单。'
    return retval

def applyMarketing(fsid):
    '''指定用户申请成为营销人员'''
    global mutex
    #目前不限时
    # if datetime.datetime.now().strftime("%H:%M:%S")<'12:00:00':
    #     return '今日还未开始，请中午12:00后再来抢！'
    limit = web.config.app_configuration.get('sys:marketing','1')
    if not str(limit).isdigit():
        limit = 1
    limit = int(limit)
    if len(web.config.today_apply)>=limit:
        return '今日名额已被抢光！请明天中午12:00再来！'
    retval = ''
    if mutex.acquire(1):
        web.config.today_apply.append(fsid)
        web.config.today_apply = list(set(web.config.today_apply))
        retval = mdb.set_saler(fsid)
        mdb.update_today_apply()
        mutex.release()
    if not retval:
        FSOBJ = mdb.get_fans_byfsid(fsid)
        if wxcode=='test':
            pushTask(mforweixin.sendTextMessage, (FSOBJ.OPENID, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'),1000)
        else:
            pushTask(mforweixin.sendMPNews, (FSOBJ.OPENID, 'cSpmz_6G_PBkj7hqA8EYpdAXzqi-wD19aL29_wPSPwQ'),1000)
        return '恭喜您，申请成功！您已成为我们的推广成员，请阅读推广计划文档了解细节。'
    else:
        return '系统繁忙！'

################################################################################
#业务处理相关
def sendDeploySuccessMessage(openid,QNOBJ):
    msg = '问卷【%s】发布成功。您可以随时在“我发布的问卷”中查看问卷统计结果。'%QNOBJ.QN_TITLE.encode('utf8')
    delaySendMessage(openid,msg)
    rtmsg = getQsArticleBody(QNOBJ,0)
    delaySendMessage(openid,rtmsg,500)


################################################################################
#管理用
def set_winaward(QNOBJ,winno,cjje,enddate):
    '''为问卷设置：中奖号、成交金额、结束日期'''
    retdat = mdb.set_award(QNOBJ.QN_ID, winno, cjje)
    if retdat.has_key('success') and retdat['success']:
        FSWIN = retdat['success']
        if mdb.canSendServiceMessage(FSWIN):
            #向中奖用户发送中奖通知。用户可能无法收到客服消息，因其主动操作已超过48小时
            rtmsg = {"title":"中奖通知","url":mforweixin.get_mp_authurl("%s/p13"%(HOST_NOS),QNOBJ.QN_ID),"description":'恭喜您！您参与的有奖问卷【%s】已中奖，奖品【%s】，请查阅中奖详情及领奖方法。'%(QNOBJ.QN_TITLE.encode('utf8'),QNOBJ.PRIZE_TITLE.encode('utf8')),"picurl":QNOBJ['SHARE_PICURL']}
            delaySendMessage(FSWIN.OPENID,rtmsg)
        #向问卷发布人发送抽奖结果通知。问卷发布人是当天结束问卷的，他的主动操作在48小时内，是可以收到客服消息的
        FSOBJ = mdb.get_fans_byfsid(QNOBJ.FS_ID)
        if mdb.canSendServiceMessage(FSOBJ):
            rtmsg = {"title":"开奖通知","url":mforweixin.get_mp_authurl("%s/p23"%(HOST_NOS)),"description":'您发布的有奖问卷【%s】已完成抽奖，请查阅开奖详情。'%(QNOBJ.QN_TITLE.encode('utf8')),"picurl":QNOBJ['SHARE_PICURL']}
            delaySendMessage(FSOBJ.OPENID,rtmsg)
        mdb.set_qsend(QNOBJ.QN_ID,enddate)
        return ''
    else:
        print 'ExceptionLottery:',QNOBJ.QN_ID,retdat['error']
        return retdat['error']

def daily_draw(yyyymmdd):
    '''以指定日期为基准处理待抽奖的问卷'''
    retval = '\n获取%s行情'%yyyymmdd
    cjje = mdb.catch_hq(yyyymmdd)
    if cjje.has_key('success'):
        cjje = cjje['success']
        retval += '：%ld'%cjje
        #DEBUG:暂时在日结时不做抽奖，只抓行情，以方便手工查看和干预
        needdraw = [] #mdb.list_needdraw()
        if needdraw:
            retval += '\n处理有奖问卷抽奖个数：%d'%len(needdraw)
        errcount = 0
        for QNOBJ in needdraw:
            winno = cjje%QNOBJ.NUM_LOTTERY+1
            if set_winaward(QNOBJ, winno, cjje, yyyymmdd):
                errcount += 1
        if errcount:
            retval += '，有%d个出现错误'%errcount
    else:
        retval += '：'+cjje['error']
    return retval
def dailyWork(fromuser='',today=None):
    '''每日结算(深交所收盘后)：1统计每日数据；2为已结束的未抽奖的有奖问卷抽奖；3问卷归档；4营销推广统计；5同步static；6清除问卷发送缓存'''
    retval = ''
    if not today:
        today = datetime.datetime.today().strftime("%Y%m%d")
    #1保存日统计数据
    import madmin
    retdat = madmin.stat_daily(today)
    for key, val in retdat:
        retval += '\n%s: %s'%(key,val)
    #2抓取行情，处理需要抽奖的问卷
    retval += daily_draw(today)
    #3问卷归档：已结束的超过90天的问卷移到主归档表；主归档表中上一年度的问卷移到年度归档表
    retval += '\n本年问卷归档'
    bef90 = formatting.format_date(formatting.date_add(-90),'%Y%m%d')
    retdat = mdb.archive_qsnaire(bef90)
    if retdat.has_key('error'):
        retval += '：'+retdat['error']
    else:
        retval += '：'+retdat['success']
    retval += '\n往年问卷归档'
    curryear = datetime.datetime.now().year
    retdat = mdb.archive_year(str(curryear-1))
    if retdat.has_key('error'):
        retval += '：'+retdat['error']
    else:
        retval += '：'+retdat['success']
    madmin.set_daily_summary(today, retval)
    #4营销推广统计
    retval += '\n营销推广统计：直接粉%d，间接粉%d'%madmin.stat_market(today)
    #5同步static到COS(这是为了能够上传白天正常操作时上传失败的文件)
    import mqcloud
    if mqcloud.cos_init(web.config.app_configuration.get('sys:cos_bucket','')):
        mqcloud.sync_upload_cos('static') #同步static目录到COS
    #6清除问卷发送缓存
    cacher_naire_sent.cleanup()
    #发送结果
    if not fromuser:
        admin_fsids = madmin.get_administrators()
        FSOBJ = mdb.get_fans_byfsid(admin_fsids[-1:][0])
        fromuser = FSOBJ.OPENID if FSOBJ else ''
    if fromuser:
        delaySendMessage(fromuser,retval.strip(),0)
    #
    web.config.today_apply = []
    mdb.update_today_apply()
    return retval.strip()

def previewLottery(fromuser):
    '''预览抽奖'''
    import madmin,mforweixin
    retval = ''
    today = datetime.datetime.today().strftime("%Y%m%d")
    retval = '获取%s行情'%today
    cjje = mdb.catch_hq(today)
    if cjje.has_key('success'):
        cjje = cjje['success']
        retval += '：%ld'%cjje
    else:
        retval += '：'+cjje['error']
    prelott = madmin.list_prelotqs()
    retval += '\n可预览抽签问卷个数：%d'%len(prelott)
    retmsg = {"title":"预览抽奖", "url":mforweixin.get_mp_authurl("%s/admin/prelottery"%(HOST_NOS)), "description":retval}
    delaySendMessage(fromuser,retmsg,0)
    return retval

def sendUncompleteMsg():
    '''取前一天发的问卷但未发布的，提醒发布人'''
    yesterday = formatting.date_add(-1)
    yesterday = yesterday.strftime("%Y%m%d")
    m = mdb.list_uncomplete_naire(yesterday)
    retval = []
    #利用groupby分组
    from itertools import groupby
    group_result = groupby(m, lambda item:item['FS_ID'])
    #生成分组后的组+明细结果集
    for k, group in group_result :
        retval.append(web.Storage({"FS_ID":k,"DETAILS":list(group)}))
    msgme = '有%d个用户存在未完成的问卷'%len(retval) if retval else ''
    for x in retval:
        msg = '温馨提示：您昨天有%d个问卷没有完成发布，您可以点击【发问卷】-【我发布的问卷】菜单查看。每个问卷的右侧有一个三形图标，可以点击它打开问卷操作菜单，继续编辑问卷完成发布。问卷只有发布了才有作用哦！专业的说法叫开始回收^_^。如果您创建的是普通问卷，别忘了发布后把问卷链接分享给调查目标，或者分享给朋友们，否则不会有人来填问卷呢！\n\n以下是昨日未完成的问卷：'%len(x['DETAILS'])
        openid = ''
        for idx, y in enumerate(x['DETAILS'],1):
            openid = y.OPENID
            msg += '\n%d.%s'%(idx,y['QN_TITLE'].encode('utf8'))
            msgme += '\n%d. %d%s'%(idx,y['QN_TYPE'],y['QN_TITLE'].encode('utf8'))
        if openid:
            pushTask(mforweixin.sendTextMessage, (openid, msg))
    #给自己发个通知以便知道已经给有未完成问卷的用户发了消息
    if msgme:
        import madmin
        madmin.sendToMe(msgme)
    sendPromoteSale()
    return len(retval)

def sendPromoteSale():
    '''向加入推广计划但无引荐数据的用户发送消息，提醒他一下'''
    #用户1号加入，2号23:59统计1号推广数据，3号9:00发无推广提醒，如果用户是1号9:00前加入的，后面无任何交互的话就超过了48小时，发不到忽略不管吧
    m = mdb.list_nosale_saler()
    for x in m:
        msg = u'温馨提示：💰刚刚与您擦肩而过！您在 %s 加入了推广计划，但是还没有推广给任何人，提醒您不要忘记了哟！'%x.INSERTTIME.strftime("%Y-%m-%d")  #\ud83d\udcb8\ud83d\udcb0
        pushTask(mforweixin.sendTextMessage, (x.OPENID, msg))
    if m:
        import madmin
        madmin.sendToMe('有%d个新加入推广计划的用户当天没有产生推广数据'%len(m))

################################################################################
def startTaskDaily():
    from helpers import TaskScheduler
    #1.每天半夜的日结
    tasktime1 = str(utils.get_yyyymmdd())+' 23:59:00'
    st1 = datetime.datetime.strptime(tasktime1, "%Y%m%d %H:%M:%S")
    TaskScheduler.add_task(dailyWork, (), start_time=st1, days=1)
    #2.每天上午9点发提醒消息，提醒前一天发问卷的人，他们没有完成的问卷，继续编辑去完成它
    currtime = datetime.datetime.now().strftime('%H%M%S')
    if currtime>='090000':
        tomorow = formatting.date_add(1).strftime("%Y%m%d") #明天
        tasktime2 = tomorow+' 09:00:00'
    else:
        tasktime2 = str(utils.get_yyyymmdd())+' 09:00:00'
    st2 = datetime.datetime.strptime(tasktime2, "%Y%m%d %H:%M:%S")
    TaskScheduler.add_task(sendUncompleteMsg, (), start_time=st2, days=1)
    #3.给自己发一个通知说明系统运行起来了
    retval = 'Running: '+datetime.datetime.now().strftime('%H:%M:%S')
    retval += '\nWork1: '+st1.strftime("%m%d %H:%M:%S")
    retval += '\nWork2: '+st2.strftime("%m%d %H:%M:%S")
    import madmin
    madmin.sendToMe(retval)
    return retval

################################################################################
def injectAD(pagedata):
    '''注入广告'''
    # pagedata['INJECTAD'] = '<a href="http://mp.weixin.qq.com/s/_xm_DkgfKGXEnt4FXyO5ig">加入推广计划，轻松赚零花钱，点击查看详情</a><br><br><br>'
    if pagedata.get('QNOBJ'):
        injectad = mdb.get_ad_byqn(pagedata['QNOBJ'].QN_ID)
    else:
        injectad = web.config.app_configuration.get('sys:injectad','')
    pagedata['INJECTAD'] = injectad


################################################################################
def test():
    print formatting.json_string(replyClick31('olJ2zuADCnfNFhGimO_6ggECTvTs'))

