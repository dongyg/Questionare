#-*- encoding: utf-8 -*-

from config import *

import mdb

def get_administrators():
    return json.loads(web.config.app_configuration.get('sys:administrators','[10000,30515173]'))
def get_salers():
    return web.config.app_configuration.get('run:saler',[])

################################################################################
#测试和管理用
def sendToMe(msg):
    if wxcode=='diaochadashi':
        openid = 'ovZQXwHJuO1LPrgefXp-oV-FsWkg' #695423523在调查大师的openid
    else:
        openid = 'olJ2zuIjHKUyDLyWsu6y0ZkPvcdA' #695423523在test的openid
    from models import mforweixin
    if isinstance(msg, list) or isinstance(msg, dict):
        return mforweixin.sendLinkRTMessage(openid,msg)
    else:
        return mforweixin.sendTextMessage(openid,msg)

def testWxpay():
    #测试：统一下单
    #201702112330521523373790
    from models import mforweixin
    retval = mforweixin.wxpay_unifiedorder('红包问卷-红包款','201702112341400977315228',1,'220.184.21.8','ovZQXwJQB1vGrk8jBqXAG7qUuM7Y')
    #返回 {'success': 'wx201702121119313203973b020688299561'}
    print retval
def testSendlink():
    #测试：发送测试支付链接。从公号往粉丝号发
    #https://dev.aifetel.cc/jsapi/hong2?fsid=299520362&r=f12d20f0f0ce11e6add39cf387b1feac&qnid=p25d28abf06f11e684b69cf387b1feac
    msg = {"title":"测试微信支付","url":"https://dev.aifetel.cc/jsapi/hong2?fsid=299520362&r=f12d20f0f0ce11e6add39cf387b1feac&qnid=p25d28abf06f11e684b69cf387b1feac","description":'',"picurl":""}
    print sendToMe(msg)
def testSendQnaire(qnid):
    #将指定问卷图文消息发送给695423523
    from models import mdb,mqsnaire
    msg = mqsnaire.getQsArticleBody(mdb.get_naire(qnid))
    print sendToMe(msg)
def loopSendQN(qnids,fsids=[]):
    #循环向粉丝发指定问卷
    qnlist = dbFrame.select("QN_NAIRE",vars=locals(),where="QN_ID in $qnids").list()
    qnlist = [mdb.append_naire_imgurl(x) for x in qnlist]
    qnlist = [mqsnaire.getQsArticleBody(x,i) for i,x in enumerate(qnlist)]
    qnlist = [x for x in qnlist if x]
    fslist = dbFrame.select("WX_FANS",vars=locals(),where="SUBSCRIBE=1 AND FS_ID NOT IN (SELECT FS_ID FROM QN_ANSWERS WHERE QN_ID NOT IN $qnids)").list()
    for fsobj in fslist:
        if mdb.canSendServiceMessage(fsobj) and (not fsids or fsobj.FS_ID in fsids):
            print fsobj.FS_ID,
            print mforweixin.sendLinkRTMessage(fsobj.OPENID,qnlist)
            time.sleep(1)
def getSJSHQ(today=None):
    '''获取指定日期的SJSHQ，如果未传日期就取系统日期'''
    if not today:
        today = datetime.datetime.today().strftime("%Y%m%d")
    import mqsnaire
    print mqsnaire.daily_draw(today)
def reloadFans():
    '''调用微信接口获取所有粉丝列表，修正数据库中的粉丝数据'''
    import mforweixin
    nextopenid = web.config.app_configuration.get('sys:next_openid','')
    retdat = mforweixin.get_fanslist(nextopenid)
    while isinstance(retdat,dict) and retdat.get('data'):
        dbFrame.delete("WX_USERS",where="1=1")
        dbFrame.multiple_insert("WX_USERS",[{"OPENID":x} for x in retdat['data']['openid']])
        if retdat['total']>retdat['count']:
            retdat = mforweixin.get_fanslist(retdat['next_openid'])
        else:
            break
    #保存next_openid
    if isinstance(retdat,dict) and retdat.get('next_openid',''):
        dbFrame.update("QN_CONFIGURATION",where="CFG_KEY='sys:next_openid'",CFG_VAL=retdat.get('next_openid',''))
        #插入缺少的粉丝
        for x in dbFrame.query("select * from WX_USERS u where not exists(select * from WX_FANS f where F.OPENID=U.OPENID)").list():
            print mforweixin.set_weixinfan(x.OPENID)
        #修正已关注的用户
        print dbFrame.query("update WX_FANS F set SUBSCRIBE=1 where exists(select * from WX_USERS U where F.OPENID=U.OPENID)")
        #修正取消关注的用户
        print dbFrame.query("update WX_FANS F set SUBSCRIBE=0 where not exists(select * from WX_USERS U where F.OPENID=U.OPENID) and F.SUBSCRIBE=1")
        #返回总用户数
    return retdat.get('total',retdat.get('errmsg','Unknown'))

def repairRedSend(fsid=None):
    '''重发因出错没有发出的红包'''
    # 查QN_REDCACHE中未正确取出放到QN_REDSERIAL中的数据
    # select FS_ID, SUM(CC_HONGBAO) from QN_REDCACHE group by FS_ID having SUM(CC_HONGBAO)>=1;
    if fsid:
        m = dbFrame.select("QN_REDSERIAL",vars=locals(),where="FCT_HONGBAO IS NULL AND FS_ID=$fsid",order="INPUT_TIME").list()
    else:
        m = dbFrame.select("QN_REDSERIAL",where="FCT_HONGBAO IS NULL",order="INPUT_TIME").list()
    for x in m:
        print x.FS_ID,x.INPUT_TIME,x.PAY_HONGBAO,x.BILL_NO
        if wxcode!='test': #测试号不发红包
            import mqsnaire
            mqsnaire.sendredpack(x.OPENID,float(x.PAY_HONGBAO),x.BILL_NO) #这个是延时异步执行的，所以不检查返回
            time.sleep(5) #等待足够长的时间

def getMaterialList():
    '''获取素材列表，打印id和title'''
    from models import mforweixin
    m = mforweixin.listMaterials()
    m = json.loads(m)
    print m['total_count']
    for x in m['item']:
        print x['media_id']
        for y in x['content']['news_item']:
            print y['title']

def generate_lottery(qnid,deadline,mins,maxs):
    '''按指定的规则生成抽奖号。deadline截止时间。min/max最小和最大间隔秒数'''
    # generate_lottery('ea3687a1114411e7b09aed5decd56ff3', '2017-03-28 20:41:50', mins=1, maxs=5)
    import random
    deadtime = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
    print datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    i = 0
    while datetime.datetime.now()<deadtime:
        delay = int(round(random.random()*(maxs-mins),0)+mins)
        sys.stdout.write('>%d'%delay)
        sys.stdout.flush()
        i += 1
        time.sleep(delay)
        t = dbFrame.transaction()
        try:
            dbFrame.query("INSERT INTO QN_LOTTERY(LT_ID,QN_ID,LOTTERY_NO,FS_ID) SELECT replace(uuid(),'-',''),'%s',(SELECT MAX(NUM_LOTTERY)+1 FROM QN_NAIRE WHERE QN_ID = '%s'),10000"%(qnid,qnid))
            dbFrame.query("UPDATE QN_NAIRE SET NUM_LOTTERY=NUM_LOTTERY+1 WHERE QN_ID = '%s'"%qnid)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
        else:
            t.commit()
    print '\nTotal:',i
    print datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

################################################################################
def list_hq_from(yyyymmdd):
    '''取指定日期及其以后的行情'''
    return dbFrame.select("SJSHQ",vars=locals(),where="HQRQ>=$yyyymmdd").list()
def list_prelotqs():
    '''返回可以预览抽奖的问卷：自主发的问卷，非自主发的已结束问卷'''
    admin_fsids = get_administrators()
    retval = dbFrame.select("QN_NAIRE",vars=locals(),where="QN_TYPE=1 AND END_DATE IS NULL AND ((QN_STATUS=9) or (FS_ID in $admin_fsids AND QN_STATUS<10))").list()
    for QNOBJ in retval:
        QNOBJ.ISSELF = QNOBJ.FS_ID in admin_fsids
        m = web.listget(dbFrame.select("QN_ANSWERS",what="max(INPUT_TIME) LAST_TIME",vars=locals(),where="QN_ID=$QNOBJ.QN_ID").list(),0,None)
        QNOBJ.LAST_TIME = m.LAST_TIME if m else None
        bNeedPresume = True
        if QNOBJ.LAST_TIME:
            hhmm = int(QNOBJ.LAST_TIME.strftime('%H%M'))
            minhqrq = formatting.date_add(1,QNOBJ.LAST_TIME) if hhmm>=1600 else QNOBJ.LAST_TIME
            yyyymmdd = int(minhqrq.strftime('%Y%m%d'))
            QNOBJ['PRELOTT'] = list_hq_from(yyyymmdd)
            for d in QNOBJ['PRELOTT']:
                d['WINNO'] = d.HQCJJE%QNOBJ.NUM_LOTTERY+1
                FSWIN = mdb.get_winfs(QNOBJ.QN_ID,d['WINNO'])
                if FSWIN:
                    d['FSID'],d['OPENID'] = FSWIN.FS_ID, FSWIN.OPENID
                d['BINGO'] = d.get('FSID') in web.config.app_configuration.get('run:selfman',admin_fsids)
                bNeedPresume = bNeedPresume and not d['BINGO']
            if bNeedPresume: #如果全部没中，再循环一次为每日行情进行假设
                for d in QNOBJ['PRELOTT']:
                    ansno = [x.ANSWER_NO for x in dbFrame.select("QN_ANSWERS",what="ANSWER_NO",vars=locals(),where="QN_ID=$QNOBJ.QN_ID AND FS_ID in $admin_fsids").list()]
                    ansno = ansno+[x.LOTTERY_NO for x in dbFrame.select("QN_LOTTERY",what="LOTTERY_NO",vars=locals(),where="QN_ID=$QNOBJ.QN_ID AND FS_ID in $admin_fsids").list()]
                    if ansno:
                        i = 1
                        bBing = False
                        while QNOBJ.NUM_LOTTERY+i<=QNOBJ.NUM_VOTE*2 and not bBing: #限制尝试次数，因为抽奖号最多是参与人数的2倍
                            winno = d.HQCJJE%(QNOBJ.NUM_LOTTERY+i)+1
                            ansno.append(QNOBJ.NUM_LOTTERY+i)
                            # print (QNOBJ.NUM_LOTTERY+i), winno
                            bBing = winno in ansno
                            if bBing:
                                d['GOTADD'] = i
                                d['GOTCHA'] = '+%d=%d@%d'%(i,QNOBJ.NUM_LOTTERY+i,winno)
                                break
                            i += 1
    return retval

def set_lottery(qnid,hqrq,addnum):
    '''采用指定的摇号方案'''
    import mqsnaire
    QNOBJ = mdb.get_naire(qnid)
    cjje = mdb.catch_hq(hqrq).get('success')
    if not cjje:
        return {'error':'无行情数据'}
    t = dbFrame.transaction()
    try:
        if addnum>0:
            dbFrame.update("QN_NAIRE",vars=locals(),where='QN_ID=$qnid',NUM_LOTTERY=web.SQLLiteral("NUM_LOTTERY+%d"%addnum))
            for x in xrange(1,addnum+1):
                dbFrame.insert('QN_LOTTERY',LT_ID=utils.get_keyword(),QN_ID=qnid,FS_ID=10000,LOTTERY_NO=QNOBJ.NUM_LOTTERY+x)
        winno = cjje%(QNOBJ.NUM_LOTTERY+addnum)+1
        mqsnaire.set_winaward(QNOBJ,winno,cjje,hqrq)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':winno}

################################################################################
def pack_stat(day,data):
    '''将日统计数据拼成[(标题,数据值)...]的形式返回'''
    if not data:
        return [('昨日','无统计数据')]
    else:
        return [("日期",day),
            ("总用户数", data["USER_TOTAL"]),
            ("其中粉丝数", data["USER_FAN"]),
            ("活跃用户数", data["USER_ACTIVE"]),
            ("新增用户数", data["NEW_TOTAL"]),
            ("其中粉丝数", data["NEW_FAN"]),
            ("新增普通问卷个数", str(data["QS_0STATUS2"])+'/'+str(data["QS_0NEW"])),
            ("新增有奖问卷个数", str(data["QS_1STATUS2"])+'/'+str(data["QS_1NEW"])),
            ("新增有奖问卷奖品金额", '%.2f/%.2f'%(data["QS_1MNY2"],data["QS_1MNY"])),
            ("新增红包问卷个数", str(data["QS_2STATUS2"])+'/'+str(data["QS_2NEW"])),
            ("新增红包问卷红包金额", '%.2f/%.2f'%(data["QS_2MNY2"],data["QS_2MNY"])),
            ("新增互助问卷个数", str(data["QS_3STATUS2"])+'/'+str(data["QS_3NEW"])),
            ("答卷份数", str(data["QS_ANSCOUNT"])),
            ("收入保证金和红包款", data["PAY_INCOME"]),
            ("支出红包款", data["PAY_HONGBAO"])
        ]
def get_lastday_stat():
    '''取昨天的日统计数据'''
    yesterday = formatting.date_add(-1)
    yesterday = yesterday.strftime("%Y%m%d")
    currSD = web.listget(dbFrame.select("ST_DAILY",vars=locals(),where="SD_DATE=$yesterday").list(),0,None)
    return pack_stat(yesterday,currSD)
def stat_daily(today=None):
    '''每日统计。只支持在当天统计，比如总用户数没有办法统计历史的'''
    if not today:
        today = datetime.datetime.today().strftime("%Y%m%d")
    currSD = web.listget(dbFrame.select("ST_DAILY",vars=locals(),where="SD_DATE=$today").list(),0,None)
    if currSD:
        data = currSD
    else:
        lastSD = web.listget(dbFrame.query("SELECT * FROM ST_DAILY WHERE SD_DATE=(SELECT MAX(SD_DATE) FROM ST_DAILY)"),0,None)
        #取用户统计数据
        user_total = web.listget(dbFrame.select("WX_FANS",what="COUNT(*) CNT").list(),0,{}).get('CNT',0)
        user_fan = web.listget(dbFrame.select("WX_FANS",what="COUNT(*) CNT",where="SUBSCRIBE=1").list(),0,{}).get('CNT',0)
        user_active = web.listget(dbFrame.select("WX_FANS",vars=locals(),what="COUNT(*) CNT",where="DATE_FORMAT(LASTACTIVETIME,'%Y%m%d')=$today").list(),0,{}).get('CNT',0)
        data = {
            'USER_TOTAL': user_total,
            'USER_FAN': user_fan,
            'USER_ACTIVE': user_active,
            'NEW_TOTAL': user_total-(lastSD.USER_TOTAL if lastSD else 0),
            'NEW_FAN': user_fan-(lastSD.USER_FAN if lastSD else 0)
        }
        #取问卷统计数据
        #
        qs_0new = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT",vars=locals(),where="QN_TYPE=0 AND INPUT_TIME=$today").list(),0,{}).get('CNT',0)
        qs_0status2 = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT",vars=locals(),where="QN_TYPE=0 AND QN_STATUS>=2 AND INPUT_TIME=$today").list(),0,{}).get('CNT',0)
        data['QS_0NEW'] = qs_0new
        data['QS_0STATUS2'] = qs_0status2
        #
        m = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT,SUM(PRIZE_VALUE) PRIZE_VALUE",vars=locals(),where="QN_TYPE=1 AND INPUT_TIME=$today").list(),0,{})
        qs_1new = m.CNT if m and m.CNT else 0
        qs_1mny = m.PRIZE_VALUE if m and m.PRIZE_VALUE else 0
        m = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT,SUM(NUM_PAY) NUM_PAY",vars=locals(),where="QN_TYPE=1 AND QN_STATUS>=2 AND INPUT_TIME=$today").list(),0,{})
        qs_1status2 = m.CNT if m and m.CNT else 0
        qs_1mny2 = m.NUM_PAY if m and m.NUM_PAY else 0
        data['QS_1NEW'] = qs_1new
        data['QS_1STATUS2'] = qs_1status2
        data['QS_1MNY'] = qs_1mny
        data['QS_1MNY2'] = qs_1mny2
        #
        m = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT,SUM(PRIZE_VALUE) PRIZE_VALUE",vars=locals(),where="QN_TYPE=2 AND INPUT_TIME=$today").list(),0,{})
        qs_2new = m.CNT if m and m.CNT else 0
        qs_2mny = m.PRIZE_VALUE if m and m.PRIZE_VALUE else 0
        m = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT,SUM(NUM_PAY) NUM_PAY",vars=locals(),where="QN_TYPE=2 AND QN_STATUS>=2 AND INPUT_TIME=$today").list(),0,{})
        qs_2status2 = m.CNT if m and m.CNT else 0
        qs_2mny2 = m.NUM_PAY if m and m.NUM_PAY else 0
        data['QS_2NEW'] = qs_2new
        data['QS_2STATUS2'] = qs_2status2
        data['QS_2MNY'] = qs_2mny
        data['QS_2MNY2'] = qs_2mny2
        #
        qs_3new = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT",vars=locals(),where="QN_TYPE=3 AND INPUT_TIME=$today").list(),0,{}).get('CNT',0)
        qs_3status2 = web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT",vars=locals(),where="QN_TYPE=3 AND QN_STATUS>=2 AND INPUT_TIME=$today").list(),0,{}).get('CNT',0)
        data['QS_3NEW'] = qs_3new
        data['QS_3STATUS2'] = qs_3status2
        #
        data['QS_ANSCOUNT'] = web.listget(dbFrame.select("QN_ANSWERS",what="COUNT(*) CNT",vars=locals(),where="DATE_FORMAT(INPUT_TIME,'%Y%m%d')=$today").list(),0,{}).get('CNT',0)
        #收入和支出统计
        m = web.listget(dbFrame.select("QN_WXPAYINCOME",what="SUM(FACT_PAY) FACT_PAY",vars=locals(),where="LEFT(TIME_END,8)=$today").list(),0,None)
        data['PAY_INCOME'] = m.FACT_PAY if m and m.FACT_PAY else 0
        m = web.listget(dbFrame.select("QN_REDSERIAL",what="SUM(PAY_HONGBAO) PAY_HONGBAO",vars=locals(),where="LEFT(INPUT_TIME,8)=$today").list(),0,None)
        data['PAY_HONGBAO'] = m.PAY_HONGBAO if m and m.PAY_HONGBAO else 0
        #保存到表中
        t = dbFrame.transaction()
        try:
            if currSD:
                dbFrame.update("ST_DAILY",vars=locals(),where="SD_DATE=$today",**data)
            else:
                dbFrame.insert("ST_DAILY",SD_DATE=today,**data)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return str(e)
        else:
            t.commit()
    return pack_stat(today,data)

def set_daily_summary(yyyymmdd,summary):
    '''保存日结结果描述'''
    t = dbFrame.transaction()
    try:
        dbFrame.update("ST_DAILY",vars=locals(),where="SD_DATE=$yyyymmdd",SUMMARY=summary)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return str(e)
    else:
        t.commit()

def list_daily(d):
    '''查询日统计数据，d为查询过去d天的数据'''
    lastm = (datetime.date.today() + datetime.timedelta(days=-int(d))).strftime('%Y%m%d')
    retval = dbFrame.select("ST_DAILY",vars=locals(),where="SD_DATE>$lastm",order="SD_DATE").list()
    for x in retval:
        x['SD_DATE'] = str(x.SD_DATE)[4:]
        # x['SD_DATE'] = x['SD_DATE'][:2]+'-'+x['SD_DATE'][2:]
    return retval

################################################################################
def calc_market(yyyymmdd,beforday,fsid,sceneid):
    '''统计指定营销人员直接粉和间接粉，保存统计数据，统计1天前的'''
    #统计推广直接粉和间接粉
    #直接粉：根据 WX_FANS.INSERTTIME 进入的时间和引荐人+关注状态计算，INSERTTIME的值只会写一次，不会重复统计
    c1 = web.listget(dbFrame.select("WX_FANS",what="count(*) CNT",vars=locals(),where="(IN_BY=$fsid OR IN_BY=$sceneid) AND DATE_FORMAT(INSERTTIME,'%Y%m%d')=$beforday AND SUBSCRIBE=1").list(),0,{}).get('CNT',0)
    #间接粉：根据 QN_ANSWERS
    c2 = web.listget(dbFrame.query("SELECT count(*) CNT FROM QN_ANSWERS A, WX_FANS F WHERE EXISTS(SELECT * FROM QN_NAIRE N WHERE EXISTS(SELECT * FROM WX_FANS F WHERE (IN_BY=$fsid OR IN_BY=$sceneid) AND F.FS_ID=N.FS_ID) AND A.QN_ID=N.QN_ID) AND ISNEW=1 AND A.FS_ID=F.FS_ID AND F.SUBSCRIBE=1 AND DATE_FORMAT(F.INSERTTIME,'%Y%m%d')=$beforday",vars=locals()).list(),0,{}).get('CNT',0)
    currMD = web.listget(dbFrame.select("WX_MARKETDETAIL",vars=locals(),where="YYYYMMDD=$yyyymmdd AND FS_ID=$fsid").list(),0,None)
    t = dbFrame.transaction()
    try:
        if not currMD:
            dbFrame.insert("WX_MARKETDETAIL",MD_ID=utils.get_keyword(),YYYYMMDD=yyyymmdd,DATE_D1=beforday,FS_ID=fsid,COUNT_D1=c1,COUNT_D2=c2,MONEY_D1=c1*0.1,MONEY_D2=c2*0.01)
        else:
            dbFrame.update("WX_MARKETDETAIL",vars=locals(),where="YYYYMMDD=$yyyymmdd AND FS_ID=$fsid",COUNT_D1=c1,COUNT_D2=c2,MONEY_D1=c1*0.1,MONEY_D2=c2*0.01)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return str(e)
    else:
        t.commit()
    return c1,c2
def stat_market(yyyymmdd='',keepdays=-1):
    '''统计所有营销人员直接粉和间接粉，保存统计数据。yyyymmdd为基准日期，通常不传或传空取系统日期。keepdays为向前几天，即统计几天前的数据，作用是判断几天前加入的用户现在还是粉丝'''
    if not yyyymmdd:
        yyyymmdd = datetime.datetime.today().strftime("%Y%m%d")
    currday = datetime.datetime.strptime(yyyymmdd, "%Y%m%d")
    beforday = formatting.date_add(keepdays,currday).strftime("%Y%m%d") #n天前
    retval = [yyyymmdd]
    t1 = 0; t2 = 0; #不含自己人的直接粉和间接粉总数
    selfman = web.config.app_configuration.get('run:selfman',get_administrators())
    m = dbFrame.select("WX_QRCODE",vars=locals(),where="IS_SALER=1 AND DATE_FORMAT(INSERTTIME,'%Y%m%d')<=$beforday").list()
    for x in m:
        c1, c2 = calc_market(yyyymmdd,beforday,x.BUSI_ID,x.SCENE_ID)
        if x.BUSI_ID not in selfman: #函数返回值不含自己人的
            t1 += c1;  t2 += c2;
            if c1 and c2:
                retval.append('%d: 直接粉%d 间接粉%d'%(x.BUSI_ID, c1,c2))
    # return '\n'.join(retval)
    return t1,t2  #返回不含自己人的直接粉和间接粉总数

def get_market_qr(fsid):
    '''返回指定营销人员的二维码ticket'''
    SLOBJ = web.listget(dbFrame.select("WX_QRCODE",vars=locals(),where="BUSI_ID=$fsid").list(),0,None)
    if SLOBJ and not SLOBJ.QR_TICKET:
        import mforweixin
        qret = mforweixin.get_qrwithparam(SLOBJ.SCENE_ID,True)
        if qret.has_key('sceneid') and qret.has_key('ticket'):
            SLOBJ.QR_TICKET = qret['ticket']
    if SLOBJ and SLOBJ.QR_TICKET:
        return SLOBJ.QR_TICKET
    else:
        return ''
def get_market_byfs(fsid):
    '''获取指定营销人员的推广统计数据，不返回金额为0的'''
    retval = dbFrame.select("WX_MARKETDETAIL",vars=locals(),where="FS_ID=$fsid AND (MONEY_D1>0 or MONEY_D2>0)",order="YYYYMMDD desc").list()
    return retval

def list_market(yyyymmdd=''):
    '''返回指定日期前7天的营销推广数据'''
    if not yyyymmdd:
        yyyymmdd = datetime.datetime.today().strftime("%Y%m%d")
    currday = datetime.datetime.strptime(yyyymmdd, "%Y%m%d")
    befor7 = formatting.date_add(-7,currday).strftime("%Y%m%d") #7天前
    selfman = [] #web.config.app_configuration.get('run:selfman',get_administrators())
    if selfman:
        m = dbFrame.select("WX_MARKETDETAIL",vars=locals(),where="YYYYMMDD>=$befor7 AND (COUNT_D1>0 or COUNT_D2>0) AND FS_ID NOT IN $selfman",
            order="YYYYMMDD DESC, COUNT_D1 DESC, COUNT_D2 DESC").list()
    else:
        m = dbFrame.select("WX_MARKETDETAIL",vars=locals(),where="YYYYMMDD>=$befor7 AND (COUNT_D1>0 or COUNT_D2>0)",
            order="YYYYMMDD DESC, COUNT_D1 DESC, COUNT_D2 DESC").list()
    retval = []
    #利用groupby分组
    from itertools import groupby
    group_result = groupby(m, lambda item:item['YYYYMMDD'])
    #生成分组后的组+明细结果集
    for k, group in group_result :
        retval.append(web.Storage({"YYYYMMDD":k,"DETAILS":list(group)}))
    #汇总一些字段
    for x in retval:
        x['SALER_COUNT'] = len(x['DETAILS'])
        x['SUM_D1_COUNT'] = sum([y.COUNT_D1 for y in x['DETAILS']])
        x['SUM_D2_COUNT'] = sum([y.COUNT_D2 for y in x['DETAILS']])
        x['SUM_D1_MONEY'] = sum([y.MONEY_D1 for y in x['DETAILS']])
        x['SUM_D2_MONEY'] = sum([y.MONEY_D2 for y in x['DETAILS']])
    return retval

def pay_market(yyyymmdd,fsid):
    '''支付指定日期指定营销人员的推广报酬'''
    m = web.listget(dbFrame.select("WX_MARKETDETAIL",vars=locals(),where="FS_ID=$fsid AND YYYYMMDD=$yyyymmdd").list(),0,None)
    if not m:
        return {'error':'推广数据不存在！'}
    if m and m.STATUS>0:
        return {'error':'该笔推广已经支付！'}
    amount = float(m.MONEY_D1)+float(m.MONEY_D2)
    if m and (amount<=0):
        return {'error':'报酬为零！'}
    FSOBJ = mdb.get_fans_byfsid(fsid)
    t = dbFrame.transaction()
    try:
        dbFrame.update("WX_MARKETDETAIL",vars=locals(),where="YYYYMMDD=$yyyymmdd AND FS_ID=$fsid",STATUS=1)
        dbFrame.insert("QN_REDCACHE",CC_ID=utils.get_keyword(),OPENID=FSOBJ.OPENID,FS_ID=FSOBJ.FS_ID,QN_ID=yyyymmdd,AN_ID='',CC_HONGBAO=amount,SUMMARY='推广报酬')
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':str(e)}
    else:
        t.commit()
    retdat = mdb.check_wxpay_hong_and_send(fsid)
    return retdat

################################################################################
def check_hong_serial():
    '''核对红包明细与合计值'''
    #取红包问卷累计发放红包字段值与答卷表汇总值不相等的记录
    m = dbFrame.query("SELECT N.QN_ID,N.PRIZE_VALUE,N.HONGBAO_MNY,N.HONGBAO_NUM,N.HONGBAO_SUM,(SELECT SUM(A.AN_HONGBAO) FROM QN_ANSWERS A WHERE A.QN_ID=N.QN_ID GROUP BY A.QN_ID) AN_SUM FROM QN_NAIRE N WHERE N.QN_TYPE=2 AND N.HONGBAO_SUM=(SELECT SUM(A.AN_HONGBAO) FROM QN_ANSWERS A WHERE A.QN_ID=N.QN_ID GROUP BY A.QN_ID)").list()

################################################################################
def pure_qi_title(value):
    '''净化问卷题目，去掉前面的编号，后面的选择提示和星号'''
    #3.您比较倾向于通过网络学习或接收哪一方面的知识？* [最多选择3项]
    #注意：尾部的方括号左边有一个空格，大概是中文空格
    import re
    value = re.sub(u' \[.+\]$', '',value) #将尾部[]及其内文字删除
    while value[:1] in ('1','2','3','4','5','6','7','8','9','0','.','、'): #将头部编号删除
        value = value[1:]
    value = value.strip()
    while value[-1:] in ('*'):
        value = value[:-1]
    return value
def decode_sojump_html(qnid,value):
    '''将问卷星问卷页面html解析出来成json格式的、可直接插入到问卷表和题目表的数据'''
    import_qnobj = {}
    if not value:
        return import_qnobj
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(value, "html.parser")
    for x in soup.find_all("h1", attrs={"class": "htitle"}):
        import_qnobj["QN_TITLE"] = x.get_text().strip() #问卷标题
    for x in soup.find_all("span", attrs={"class": "description"}):
        import_qnobj['QN_SUMMARY'] = x.get_text().strip() #问卷描述
    import_qnobj['items'] = []
    for no,x in enumerate(soup.find_all("div", attrs={"class": "field-label"}),1):
        import_qnobj['QN_NO'] = no
        qnitem = {"QI_TITLE":x.get_text().strip(),"QI_NO":no,"QI_OPTION":[]} #题目
        if qnitem['QI_TITLE'].find(u'多选')>0:
            qnitem['QI_TYPE'] = 'C'
        else:
            qnitem['QI_TYPE'] = 'R'
        llen = []
        for x in soup.find_all("div", attrs={"class": "label", "for": re.compile("q%d_"%no)}):
            option = x.get_text().strip()
            llen.append(len(option))
            qnitem['QI_OPTION'].append(option) #选项
        if llen and max(llen)<=5: #如果所有选项字数不超过5个字，设置题目为标签式选择
            qnitem['QI_TYPE'] = qnitem['QI_TYPE']+('H' if qnitem['QI_TYPE']=='C' else 'A')
        qnitem['QI_TITLE'] = pure_qi_title(qnitem['QI_TITLE'])
        qnitem['QI_ID'] = utils.get_keyword()
        qnitem['QN_ID'] = qnid
        import_qnobj['items'].append(qnitem)
    import_qnobj['QN_ID'] = qnid
    return import_qnobj
def save_sojump(qnobj,fsid=0):
    '''将问卷星html解析出来的json格式的问卷保存到数据库'''
    qnitems = qnobj.pop('items',[])
    if web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="QN_ID=$qnobj['QN_ID']").list(),0,None):
        return {'error':u"%s 已存在！"%qnobj['QN_ID']}
    if not qnobj.get('FS_ID'):
        qnobj['FS_ID'] = fsid
    if not qnobj.get('INSERT_TIME'):
        qnobj['INSERT_TIME'] = utils.get_currdatetimestr(dbFrame.dbtype)
    if not qnobj.get('INPUT_TIME'):
        qnobj['INPUT_TIME'] = utils.get_yyyymmdd()
    if not qnobj.get('QN_MAX'):
        qnobj['QN_MAX'] = 100
    if not qnobj.get('QN_DEPLOY'):
        qnobj['QN_DEPLOY'] = 1
    t = dbFrame.transaction()
    try:
        dbFrame.insert("QN_NAIRE",**qnobj)
        for x in qnitems:
            if not isinstance(x['QI_OPTION'],basestring):
                x['QI_OPTION'] = json.dumps(x['QI_OPTION'],ensure_ascii=False)
            dbFrame.insert("QN_ITEMS",**x)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':str(e)}
    else:
        t.commit()
    return {'success':qnobj['QN_ID']}

