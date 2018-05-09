#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *

image_save_to_disk = True #not is_sae

################################################################################
#与数据有关的工具函数
def table_exists(conn,tbname,tbowner=''):
    """判断指定数据源中表是否存在，存在则返回数据库连接对象"""
    if 'mssql'==conn.dbtype:
        exists = bool(conn.select('sys.all_objects', what='name as TABLE_NAME', vars=locals(), where="name = $tbname and type in ('U','V')"))
    elif 'oracle'==conn.dbtype:
        #当连接数据库用户不是表属主时需要判断属主
        tbname = tbname.upper()
        if tbowner:
            exists = bool(conn.select("all_tables",what="TABLE_NAME",vars=locals(),where="OWNER=$tbowner and TABLE_NAME=$tbname") or
                        conn.select("all_views",what="VIEW_NAME TABLE_NAME",vars=locals(),where="OWNER=$tbowner and VIEW_NAME=$tbname"))
        else:
            exists = bool(conn.select("user_tables",what="TABLE_NAME",vars=locals(),where="TABLE_NAME=$tbname") or
                        conn.select("user_views",what="VIEW_NAME TABLE_NAME",vars=locals(),where="VIEW_NAME=$tbname"))
    else:
        #mysql当连接数据库用户无权访问表时，就查不到这个表名
        exists = bool(conn.select('INFORMATION_SCHEMA.TABLES', what='TABLE_NAME,TABLE_ROWS',
                    vars=locals(), where="TABLE_SCHEMA = $conn.dbname and TABLE_NAME = $tbname"))
    return exists
def get_basetitle(key,val):
    '''获取基本信息的名称，包括：年龄、婚姻状况、学历、收入'''
    data = {'AGE':{None:'未设置',2**0:'未透露',2**1:'20岁及以下',2**2:'21-25岁',2**3:'26-30岁',2**4:'31-40岁',2**5:'41-50岁',2**6:'51-60岁',2**7:'60岁以上'},
            'MARRIAGE':{None:'未设置',2**0:'未透露',2**1:'已婚',2**2:'未婚'},
            'ACADEMIC':{None:'未设置',2**0:'未透露',2**1:'初中及以下',2**2:'高中/中专',2**3:'大专',2**4:'本科',2**5:'硕士',2**6:'博士'},
            'INCOME':{None:'未设置',2**0:'未透露',2**1:'1000元以下',2**2:'1001-2000元',2**3:'2001-3000元',2**4:'3001-5000元',2**5:'5001-8000元',2**6:'8001-10000元',2**7:'10001-20000元',2**8:'20000元以上'}}
    return data.get(key,{}).get(val,'未知')
def calc_wxpay_fare(totalfee,qntype):
    '''计算微信支付手续费'''
    if isinstance(totalfee,basestring):
        totalfee = float(totalfee)
    #VARIANT:0.006是微信商户的支付手续费率
    if qntype==1:
        #有奖问卷：保证扣掉手续费后的金额等于奖品价值，不是直接乘0.006，因为支付金额加上手续费后，总金额多了，手续费也会多，所以计算方法是下面的公式，而不是直接乘0.006
        retval = totalfee/(1-0.006) - totalfee
    elif qntype==2:
        #红包问卷：用户支付为红包款总额，手续费从中扣除，因此手续费是直接乘0.006
        retval = totalfee*0.006
    return round(retval,2)

def canSendServiceMessage(FSOBJ):
    '''判断是否能发客服消息'''
    past = formatting.calc_datetime_range(FSOBJ.LASTACTIVETIME)
    return FSOBJ.OPENID and FSOBJ.SUBSCRIBE==1 and (past<48*3600)

def isValidPrepayID(prepayid):
    '''微信支付统一下单的prepay_id有效时间为2个小时。传入并解析它判断是否2个小时以内的'''
    # wx2017022108594818fb42f3590500973950
    if not prepayid:
        return False
    else:
        prepayid = prepayid[2:16]
        tpay = datetime.datetime.strptime(prepayid, "%Y%m%d%H%M%S")
        return (datetime.datetime.now()-tpay).seconds < 7000 #大于7000秒

def generateLotteryNo(QNOBJ,ANSFS):
    '''为答卷人和引荐人生成抽奖号。传入：问卷对象，答卷人对象。返回一个list，第1个值是答卷人抽奖号，第2个值是引荐人抽奖号。若不需要为引荐人生成抽奖号，list只有一个值'''
    retval = []
    retval.append(QNOBJ.NUM_LOTTERY+1) #先添加一个抽奖号
    if QNOBJ.QN_TYPE==1 and ANSFS.IN_BY!=QNOBJ.FS_ID: #有奖问卷，引荐人不是发卷人时，才为引荐人生成抽奖号
        import madmin,random
        admin_fsids = madmin.get_administrators()
        selfsent = QNOBJ.FS_ID in admin_fsids #是否自己人发的问卷，自己人发的问卷总是生成引荐人抽奖号，引荐人为10000
        #自己人发的问卷总是生成，有引荐人且不是10000的总是生成，引荐人是10000的50%概率生成
        if selfsent or (ANSFS.IN_BY and ANSFS.IN_BY!=10000) or (ANSFS.IN_BY==10000 and random.random()>0.5):
            retval.append(QNOBJ.NUM_LOTTERY+2) #再添加一个抽奖号
            if random.random()>0.5: #有2个抽奖号时50%的机率调换顺序
                retval.reverse()
    return retval

def put_image_host(imgurl):
    '''为问卷图片添加所在主机'''
    #问卷图片同步放到腾讯COS上，返回问卷信息时，为图片url添加COS的host
    if imgurl:
        if web.ctx.get('protocol')=='https':
            imghost = web.config.app_configuration.get('sys:image_host_https','')
        else:
            imghost = web.config.app_configuration.get('sys:image_host_http','')
        if not imghost:
            imghost = HOST_NOS
        imgurl = imghost+imgurl
    return imgurl

################################################################################
#粉丝管理
def get_fsid_byopenid(openid):
    '''根据openid取fsid'''
    retval = cacher_fsid_byopenid.getFSID(openid)
    if not retval:
        retval = web.listget(dbFrame.select("WX_FANS",vars=locals(),where="OPENID=$openid"),0,None)
        cacher_fsid_byopenid.set(openid,retval)
        return retval.FS_ID if retval else None
    else:
        return retval
def get_fans_byopenid(openid):
    '''根据openid获取粉丝数据'''
    retval = cacher_fsid_byopenid.get(openid)
    if not retval:
        retval = web.listget(dbFrame.select("WX_FANS",vars=locals(),where="OPENID=$openid"),0,None)
        cacher_fsid_byopenid.set(openid,retval)
    return retval
def get_fans_byfsid(fsid):
    '''根据fsid获取粉丝数据'''
    retval = cacher_fans_obj.get(fsid)
    if not retval:
        retval = web.listget(dbFrame.select("WX_FANS",vars=locals(),where="FS_ID=$fsid"),0,None)
        if retval:
            retval.pop('HEADIMGURL',None) #这3个字段没有用
            retval.pop('COUNTRY',None)
            retval.pop('UNIONID',None)
            cacher_fans_obj.set(fsid,retval)
    return retval
def get_fans_level(FSOBJ):
    '''根据用户的累计调查币（COIN_TOTAL）返回用户等级。等级用emoji表情符号表示'''
    #等级划分，依据27以上的立方数为依据
    #[27,  64,  125, 216, 343, 512, 729,  1000, 1331, 1728, 2197, 2744,]对应序号转换为5进制
    #['0', '1', '2', '3', '4', '10', '11', '12', '13', '14', '20',]
    #达到和超过一个立方数，取对应序号的4进制值，从右向左，依次分别表示从低到高级别的符号个数
    #以奖牌符号为例，可以达到效果：27时零个铜牌，64时一个铜牌，125时二个铜牌，216时三个铜牌，343时四个铜牌，512时一个银牌零个铜牌，729时一个银牌一个铜牌，以此类推
    symbol = [u'\U0001f949',u'\U0001f948',u'\U0001f947',u'\U0001f3c6'] #铜牌/银牌/金牌/奖杯
    symbol = [u'\u2b50\ufe0f',u'\U0001f319',u'\u2600\ufe0f',u'\U0001f48e',u'\U0001f451'] #星星/月亮/太阳/钻石/皇冠
    retval = ''
    if FSOBJ:
        i = 3
        while FSOBJ.COIN_TOTAL>=(i+1)**3:
            i += 1
        mstr = utils.ten_to_five(i-3)
        for idx,x in enumerate(mstr[::-1]):
            if idx>len(symbol)-1:
                idx=len(symbol)-1
            retval = symbol[idx]*int(x) + retval
    return retval.encode('utf8')

def set_fans_baseinfo(fsid,age,marriage,academic,income,sex,province,city):
    '''设置粉丝基本个人信息'''
    FSOBJ = get_fans_byfsid(fsid)
    #在支持设置性别、地区的时候，从微信获取到的用户信息会覆盖用户自己设置的信息
    # if FSOBJ and FSOBJ.OPENID:
    #     import mqsnaire,mforweixin
    #     mqsnaire.pushTask(mforweixin.get_fansinfo, FSOBJ.OPENID) #获取微信用户信息
    t = dbFrame.transaction()
    try:
        age=int(age if age and str(age).isdigit() else 0)
        marriage=int(marriage if marriage and str(marriage).isdigit() else 0)
        academic=int(academic if academic and str(academic).isdigit() else 0)
        income=int(income if income and str(income).isdigit() else 0)
        data = {"P2_AGE":2**age, "P2_MARRIAGE":2**marriage, "P2_ACADEMIC":2**academic, "P2_INCOME":2**income}
        if FSOBJ and FSOBJ.P2_AGE==None: #如果之前的数据是null说明是第一次设置，设置赠送积分
            data["COIN_TOTAL"] = (FSOBJ.COIN_TOTAL if FSOBJ.COIN_TOTAL else 0) +100
            data["COIN_HOLD"] = (FSOBJ.COIN_HOLD if FSOBJ.COIN_HOLD else 0) +100
            dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype),CHG_AMOUNT=100,CHG_TYPE=12)
            FSOBJ.update(data)
            cacher_fans_obj.set(fsid,FSOBJ) #更新缓存
            check_pause_naire3(FSOBJ)
        dbFrame.update("WX_FANS", vars=locals(), where="FS_ID=$fsid",SEX=sex,PROVINCE=province,CITY=city,**data)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return e
    else:
        t.commit()
        return '保存成功'
def add_fans_count(fsid,field,num=1):
    '''设置粉丝计数字段。field包括：COUNT_P0,COUNT_P1,COUNT_P2,COUNT_P3,COUNT_A0,COUNT_A1,COUNT_A2,COUNT_A3,SUM_A2,COUNT_WIN,GET_FANS'''
    if field not in ('COUNT_P0','COUNT_P1','COUNT_P2','COUNT_P3','COUNT_A0','COUNT_A1','COUNT_A2','COUNT_A3','SUM_A2','COUNT_WIN','GET_FANS'):
        return '计数字段无效！'
    FSOBJ = get_fans_byfsid(fsid)
    newval = (float(FSOBJ[field]) if FSOBJ[field] else 0) + num
    t = dbFrame.transaction()
    try:
        tpl = {field:newval}
        dbFrame.update("WX_FANS", vars=locals(), where="FS_ID=$fsid", **tpl)
        # cacher_fans_obj.delete(fsid)
        FSOBJ.update(tpl) #更新缓存
        cacher_fans_obj.set(fsid,FSOBJ)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return e
    else:
        t.commit()
        return ''


################################################################################
#积分管理
def set_fans_coin(FSOBJ,chgamount,chgtype,summary):
    '''粉丝积分变化'''
    fsid = FSOBJ.FS_ID
    t = dbFrame.transaction()
    try:
        cdid = utils.get_keyword()
        data = {"CD_ID":cdid,"FS_ID":fsid,"INSERTTIME":utils.get_currdatetimestr(dbFrame.dbtype),"CHG_AMOUNT":chgamount,"CHG_TYPE":chgtype,"SUMMARY":summary}
        dbFrame.insert("WX_COINDETAIL", **data)
        tpl = {"COIN_TOTAL":FSOBJ.COIN_TOTAL+(chgamount if chgamount>0 else 0), "COIN_HOLD":FSOBJ.COIN_HOLD+chgamount}
        dbFrame.update("WX_FANS", vars=locals(), where="FS_ID=$fsid", **tpl)
        FSOBJ.update(tpl)
        cacher_fans_obj.set(fsid,FSOBJ) #更新缓存
        if chgamount>0:
            check_pause_naire3(FSOBJ)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':str(e)}
    else:
        t.commit()
        return {'success':cdid}
def list_coin(fsid):
    retval = dbFrame.select("WX_COINDETAIL", vars=locals(), where="FS_ID=$fsid",order="INSERTTIME DESC").list()
    return retval
def stat_thisweek_coin():
    '''统计本个自然周的答卷获得调查币最多的用户'''
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=now.weekday())).strftime('%Y%m%d')
    week_end = (now - datetime.timedelta(days=now.weekday()-6)).strftime('%Y%m%d')
    return dbFrame.select("WX_COINDETAIL C,WX_FANS F",what="C.FS_ID,F.NICKNAME,SUM(C.CHG_AMOUNT) CHG_AMOUNT",vars=locals(),
        where="C.FS_ID=F.FS_ID AND F.SUBSCRIBE=1 AND C.CHG_TYPE IN (14,15) AND DATE_FORMAT(C.INSERTTIME,'%Y%m%d') BETWEEN $week_start AND $week_end",
        group="C.FS_ID,F.NICKNAME",order="CHG_AMOUNT DESC",limit=10).list()
def stat_lastweek_coin():
    '''统计上个自然周的答卷获得调查币最多的用户'''
    now = datetime.datetime.now()
    last_week_start = (now - datetime.timedelta(days=now.weekday()+7)).strftime('%Y%m%d')
    last_week_end = (now - datetime.timedelta(days=now.weekday()+1)).strftime('%Y%m%d')
    return dbFrame.select("WX_COINDETAIL C,WX_FANS F",what="C.FS_ID,F.NICKNAME,SUM(C.CHG_AMOUNT) CHG_AMOUNT",vars=locals(),
        where="C.FS_ID=F.FS_ID AND F.SUBSCRIBE=1 AND C.CHG_TYPE IN (14,15) AND DATE_FORMAT(C.INSERTTIME,'%Y%m%d') BETWEEN $last_week_start AND $last_week_end",
        group="C.FS_ID,F.NICKNAME",order="CHG_AMOUNT DESC",limit=10).list()
    # return dbFrame.select("WX_COINDETAIL C,WX_FANS F",what="C.FS_ID,F.NICKNAME,CHG_TYPE,SUM(C.CHG_AMOUNT) CHG_AMOUNT",
    #     vars=locals(),where="C.FS_ID=F.FS_ID",
    #     group="C.FS_ID,F.NICKNAME,CHG_TYPE",order="CHG_AMOUNT DESC",limit=10).list()

################################################################################
#粉丝统计
def stat_fans_byfsid(fsid):
    '''统计用户发了多少个问卷(无偿，有偿，红包)、答了多少个问卷(无偿，有偿，红包)、中奖几次(中奖，红包)，引荐了多少粉丝'''
    #发了多少个问卷(无偿，有偿，红包)、答了多少个问卷(无偿，有偿，红包)、中奖几次(中奖，红包)，引荐了多少粉丝
    p0, p1, p2, p3 = count_aire(fsid)
    a0, a1, a2, a3 = count_answer(fsid)
    win,suma2 = count_award(fsid)
    f1 = count_inby(fsid)
    return p0, p1, p2, p3, a0, a1, a2, a3, win, suma2, f1

def count_inby(fsid):
    '''统计用户引荐粉丝数'''
    # m = web.listget(dbFrame.select("WX_FANS",what="count(*) CNT",vars=locals(),where="IN_BY=$fsid"),0,None)
    # return m.CNT if m else 0
    FSOBJ = get_fans_byfsid(fsid)
    return (FSOBJ.GET_FANS if FSOBJ and FSOBJ.GET_FANS else 0)


################################################################################
#图片存储和读取
def set_image(imgid,imgdata,mode):
    '''保存图片。若imgid为空为新添加，否则为修改。mode:1/2/3分别代表微信消息大图/小图/奖品详情图'''
    #imgdata:页面上传进来的是 data:image/png;base64, 这种编码后的数据
    if not image_save_to_disk:
        t = dbFrame.transaction()
        try:
            if not imgid:
                imgid = utils.get_keyword()
                dbFrame.insert("QN_IMAGES",IMG_ID=imgid,CONTENT=imgdata)
            else:
                dbFrame.update("QN_IMAGES",vars=locals(),where="IMG_ID=$imgid",CONTENT=imgdata)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            retval = {"error":e}
        else:
            t.commit()
            retval = {"success":imgid}
    else:
        #此时imgid为文件存储的路径和文件名
        import mqcloud
        if not imgid:
            folder = utils.make_today_folder('static')
            imgid = os.path.join(folder,utils.get_keyword()+'.jpg')
        try:
            imgdata = formatting.base64decode(imgdata[imgdata.find('base64,')+7:])
            if mode==1:
                imgdata = image.resizeImageData(imgdata,640,320,force=True)
            elif mode==2:
                imgdata = image.resizeImageData(imgdata,80,80,force=True)
            elif mode==3:
                imgdata = image.resizeImageData(imgdata,720,0,force=False)
            fp = open(imgid,'wb')
            fp.write(imgdata)
            fp.close()
            cos_bucket = web.config.app_configuration.get('sys:cos_bucket','')
            if mqcloud.cos_init(cos_bucket):
                mqcloud.sync_files_cos([imgid], 'static_upto_cos_%s.rec'%cos_bucket)
        except Exception, e:
            traceback.print_exc()
            retval = {"error":e}
        retval = {"success":imgid}
    return retval
def del_image(imgid):
    '''删除图片'''
    if not image_save_to_disk:
        t = dbFrame.transaction()
        try:
            if isinstance(imgid,list):
                dbFrame.delete("QN_IMAGES",vars=locals(),where="IMG_ID in $imgid")
            else:
                dbFrame.delete("QN_IMAGES",vars=locals(),where="IMG_ID=$imgid")
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            retval = {"error":e}
        else:
            t.commit()
            retval = {"success":''}
    else:
        #此时imgid为文件存储的路径和文件名
        if isinstance(imgid,list):
            for x in imgid:
                if x and os.path.isfile(x):
                    os.remove(x)
        else:
            if x and os.path.isfile(imgid):
                os.remove(imgid)
        retval = {"success":''}
    return retval
def get_image(imgid):
    '''取指定图片'''
    if not image_save_to_disk:
        m = web.listget(dbFrame.select("QN_IMAGES",vars=locals(),where="IMG_ID=$imgid").list(),0,{})
        return m.get('CONTENT','')
    else:
        #图片存储在磁盘上时，实际上是不用这个来返回图片的
        if os.path.isfile(imgid):
            try:
                fp = open(imgid, 'rb')
            except IOError:
                return ''
            content = fp.read()
            fp.close()
            return 'data:image/png;base64,%s'%formatting.base64encode(content)


################################################################################
#问卷各种查询
def list_myaire(fsid):
    '''取指定用户发布的问卷。只取QN_NAIRE的，不含归档的'''
    retval = dbFrame.select("QN_NAIRE",vars=locals(),where="FS_ID=$fsid and QN_STATUS<10",order="INPUT_TIME DESC,QN_STATUS").list()
    for x in retval:
        append_naire_imgurl(x)
        if x.QN_TYPE==1 and x.WIN_NO:
            m = web.listget(dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$x.QN_ID AND ANSWER_NO=$x.WIN_NO").list(),0,None)
            x['AN_ADDRESS'] = m.AN_ADDRESS if m else ''
            x['AN_PHONE'] = m.AN_PHONE if m else ''
            x['AN_EXPNO'] = m.AN_EXPNO if m else ''
    return retval
def list_partin(fsid):
    '''取指定用户参与过的问卷。只取QN_NAIRE的，不含归档的'''
    retval = dbFrame.select("QN_NAIRE N, QN_ANSWERS A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.AN_ID,A.ANSWER_NO,A.AN_CONTENT,A.AN_HONGBAO,A.AN_ADDRESS,A.AN_PHONE,A.AN_JIANGLI",
        vars=locals(),where="N.QN_ID=A.QN_ID AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list()
    retval = [append_naire_imgurl(x) for x in retval]
    return retval
def list_award(fsid):
    '''取指定用户的中奖和获取红包记录'''
    retval = dbFrame.select("QN_NAIRE N, QN_ANSWERS A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.AN_ID,A.ANSWER_NO,A.AN_CONTENT,A.AN_HONGBAO,A.AN_ADDRESS,A.AN_PHONE,A.AN_JIANGLI",
        vars=locals(),where="N.QN_ID=A.QN_ID AND (N.WIN_NO=A.ANSWER_NO OR AN_HONGBAO>0 OR AN_JIANGLI>0) AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list()
    retval.extend(dbFrame.select("QN_NAIRE N, QN_LOTTERY A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.LT_ID AN_ID,A.LOTTERY_NO ANSWER_NO,'' AN_CONTENT,0 AN_HONGBAO,A.LT_ADDRESS AN_ADDRESS,A.LT_PHONE AN_PHONE,0 AN_JIANGLI",
        vars=locals(),where="N.QN_ID=A.QN_ID AND (N.WIN_NO=A.LOTTERY_NO) AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list())
    retval.sort(key=lambda x: x['AN_INPUT_TIME'], reverse=True)
    retval = [append_naire_imgurl(x) for x in retval]
    return retval
def get_nocomplete(fsid,qntype):
    '''检查用户是否有未完成的指定类型的问卷'''
    retval = ''
    m = dbFrame.select("QN_NAIRE",vars=locals(),where="FS_ID=$fsid and QN_TYPE in $qntype and QN_STATUS<2").list()
    if m:
        retval = '你有%d个编辑中的问卷，可进入【我发布的问卷】去编辑，如未编辑完成的问卷已无用，请删除之。\n'%len(m)+'\n'.join([str(i)+'.'+x.QN_TITLE.encode('utf8') for i,x in enumerate(m,1)])
    return retval,len(m)

def append_naire_imgurl(QNOBJ):
    '''向问卷对象添加img url等常用字段'''
    if not image_save_to_disk:
        QNOBJ['IMG1_URL'] = '/rst/image/%s/'%QNOBJ['IMG1'] if QNOBJ['IMG1'] else ''
        QNOBJ['IMG2_URL'] = '/rst/image/%s/'%QNOBJ['IMG2'] if QNOBJ['IMG2'] else ''
        QNOBJ['IMGDETAIL_URLS'] = [(x,'/rst/image/%s/'%x) for x in formatting.json_object(QNOBJ['IMGDETAIL'],[])]
    else:
        #windows系统上保存的路径分隔符是\需要替换一下
        QNOBJ['IMG1_URL'] = put_image_host( '/%s'%QNOBJ['IMG1'].replace('\\','/') if QNOBJ['IMG1'] else '' )
        QNOBJ['IMG2_URL'] = put_image_host( '/%s'%QNOBJ['IMG2'].replace('\\','/') if QNOBJ['IMG2'] else '' )
        QNOBJ['IMGDETAIL_URLS'] = [(x.replace('\\','/'),put_image_host('/%s'%x.replace('\\','/'))) for x in formatting.json_object(QNOBJ['IMGDETAIL'],[])]
    #分享链接的标题、描述、图片
    #标题：话题问卷时，只取标题。非话题问卷时，前面加上问卷类型
    #描述：有奖问卷写奖品名称。红包问卷写红包金额。普通问卷就用问卷描述（为空就写问卷调查大师）。如果是话题问卷且有红包，在红包金额前面加问卷描述（输入的姓名或昵称）
    #图片：分享链接的图片用80x80小图
    #链接：用微信网页授权跳转至link
    if QNOBJ.QN_TYPE==0:
        QNOBJ['QN_TYPENAME'] = '普通问卷'
        QNOBJ['ICON_CLASS'] = 'icon-question-sign'
        QNOBJ['SHARE_DESC'] = QNOBJ['QN_SUMMARY'].encode('utf8') if QNOBJ['QN_SUMMARY'] else '问卷调查大师'
    elif QNOBJ.QN_TYPE==1:
        QNOBJ['QN_TYPENAME'] = '有奖问卷'
        QNOBJ['ICON_CLASS'] = 'icon-trophy'
        QNOBJ['SHARE_DESC'] = '奖品：%s - 价值：%d元'%(QNOBJ.PRIZE_TITLE.encode('utf8') if QNOBJ.PRIZE_TITLE else '', QNOBJ.PRIZE_VALUE if QNOBJ.PRIZE_VALUE else 0)
    elif QNOBJ.QN_TYPE==2:
        QNOBJ['QN_TYPENAME'] = '红包问卷'
        QNOBJ['ICON_CLASS'] = 'icon-cny'
        QNOBJ['SHARE_DESC'] = (QNOBJ['QN_SUMMARY'].encode('utf8') if QNOBJ['TOPIC_QNID'] and QNOBJ['QN_SUMMARY'] else '')+'～答问卷有红包呦！'
    elif QNOBJ.QN_TYPE==3:
        QNOBJ['QN_TYPENAME'] = '互助问卷'
        QNOBJ['ICON_CLASS'] = 'icon-group'
        QNOBJ['SHARE_DESC'] = (QNOBJ['QN_SUMMARY'].encode('utf8') if QNOBJ['QN_SUMMARY'] else '')+'～互助有礼！'
    else:
        QNOBJ['QN_TYPENAME'] = ''
        QNOBJ['ICON_CLASS'] = 'icon-question-sign'
        QNOBJ['SHARE_DESC'] = (QNOBJ['QN_SUMMARY'].encode('utf8') if QNOBJ['QN_SUMMARY'] else '')
    QNOBJ['SHARE_TITLE'] = QNOBJ['QN_TITLE'].encode('utf8')
    if not (QNOBJ['TOPIC_QNID'] or QNOBJ.QN_TYPE==0):
        QNOBJ['SHARE_TITLE'] = QNOBJ['QN_TYPENAME']+' - '+QNOBJ['SHARE_TITLE']
    import mforweixin
    # QNOBJ['SHARE_LINK'] = mforweixin.get_mp_authurl("%s/link"%(HOST_NOS),QNOBJ.QN_ID)
    QNOBJ['SHARE_LINK'] = "%s/link?state=%s"%(HOST_NOS,QNOBJ.QN_ID)
    QNOBJ['SHARE_PICURL'] = QNOBJ.IMG1_URL or QNOBJ.IMG2_URL or put_image_host('/static/img/WX640_1.jpg')
    return QNOBJ
def check_naire_qr(QNOBJ):
    '''检查问卷是否有二维码，没有就生成一个'''
    if QNOBJ and not QNOBJ.SCENE_ID:
        import mforweixin
        t = dbFrame.transaction()
        try:
            savedata = {}
            qret = mforweixin.get_qrwithparam() #生成二维码并保存sceneid和ticket
            if qret.has_key('sceneid') and qret.has_key('ticket'):
                savedata['QR_TICKET'] = qret['ticket']
                savedata['SCENE_ID'] = qret['sceneid']
                QNOBJ['QR_TICKET'] = qret['ticket']
                QNOBJ['SCENE_ID'] = qret['sceneid']
            if savedata:
                dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$QNOBJ.QN_ID",**savedata)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return QNOBJ
        else:
            t.commit()
    return QNOBJ
def get_naire(qnid):
    '''取问卷信息'''
    if not qnid: return None
    retval = web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="QN_ID=$qnid").list(),0,None)
    if not retval: return None
    append_naire_imgurl(retval)
    check_naire_qr(retval)
    return retval
def get_naire_byqr(sceneid):
    '''通过二维码sceneid值获取问卷对象'''
    retval = web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="SCENE_ID=$sceneid").list(),0,None)
    if not retval: return None
    append_naire_imgurl(retval)
    return retval

def list_cananswer(fsid,qntype,cache=True):
    '''获取粉丝可以参与的问卷：回收中、有偿、筛选条件匹配，未参与过、未推送过。qntype:1有奖问卷/2红包问卷/3互助问卷。cache表示记录到缓存下次再获取时不包含'''
    FSOBJ = get_fans_byfsid(fsid)
    retval = []
    retval = dbFrame.select("QN_NAIRE",what="QN_ID,FS_ID,QN_TYPE,QN_TITLE,QN_SUMMARY,PRIZE_TITLE,PRIZE_VALUE,HONGBAO_MNY,HONGBAO_NUM,IMG1,IMG2,IMGDETAIL,TOPIC_QNID,QN_MAX,NUM_VOTE,INSERT_TIME,SCENE_ID,QR_TICKET",
        vars=locals(),
        where="FS_ID!=$fsid AND QN_ID NOT IN (SELECT QN_ID FROM QN_ANSWERS A WHERE A.FS_ID=$fsid) AND QN_STATUS=2 and QN_DEPLOY=1 and QN_TYPE=$qntype and (QN_AGE&&$FSOBJ.P2_AGE>0 or QN_AGE=0) and (QN_MARRIAGE&&$FSOBJ.P2_MARRIAGE>0 or QN_MARRIAGE=0) and (QN_ACADEMIC&&$FSOBJ.P2_ACADEMIC>0 or QN_ACADEMIC=0) and (QN_INCOME&&$FSOBJ.P2_INCOME>0 or QN_INCOME=0) and (QN_SEX=0 or QN_SEX=$FSOBJ.SEX) and (QN_CITY='不限' or QN_CITY=$FSOBJ.CITY) and (QN_PROVINCE='不限' or QN_PROVINCE=$FSOBJ.PROVINCE)",
        # where="QN_TYPE=$qntype and (QN_AGE&&$FSOBJ.P2_AGE>0 or QN_AGE=0) and (QN_MARRIAGE&&$FSOBJ.P2_MARRIAGE>0 or QN_MARRIAGE=0) and (QN_ACADEMIC&&$FSOBJ.P2_ACADEMIC>0 or QN_ACADEMIC=0) and (QN_INCOME&&$FSOBJ.P2_INCOME>0 or QN_INCOME=0) and (QN_SEX=0 or QN_SEX=$FSOBJ.SEX) and (QN_CITY='不限' or QN_CITY=$FSOBJ.CITY) and (QN_PROVINCE='不限' or QN_PROVINCE=$FSOBJ.PROVINCE)",
        order="PRIZE_VALUE DESC, INPUT_TIME").list()
    #利用缓存器过滤掉已经发送给粉丝过的问卷
    retval = [check_naire_qr(append_naire_imgurl(x)) for x in retval if (cache and fsid not in cacher_naire_sent.get(x.QN_ID)) or (not cache)]
    if retval:
        #改变排序规则，结合目标样本数/报酬多少/发布时间多个值，加权得分后排序
        max_prize = max([x.PRIZE_VALUE for x in retval])
        min_input = min([x.INSERT_TIME for x in retval])
        max_input = max([x.INSERT_TIME for x in retval])
        def calc_sortval(x):
            '''计算权重值'''
            #1.回收份数/目标样本数，得到回收率，回收率高的往后排，加权30%
            #2.报酬（奖品/红包/调查币）多的往前排，把数值归一化（需要用到待排序问卷中报酬的最大值），加权30%
            #3.发布时间早的往前排，把数值归一化（需要用到待排序问卷中问卷录入时间的最小值和最大值），加权40%
            q1 = 1-x['NUM_VOTE']*1.0/x['QN_MAX'] if x['QN_MAX']>0 else 0
            q2 = x['PRIZE_VALUE']*1.0/max_prize if max_prize>0 else 0
            q3 = 1-(x['INSERT_TIME']-min_input).total_seconds()/(max_input-min_input).total_seconds() if max_input!=min_input else 0
            return int(round((q1*0.3+q2*0.3+q3*0.4)*1000000,0))
        def compare(x,y):
            '''自定义比较函数，比较两个可参与的问卷，哪个该排在前面。x<y返回负数，x>y返回正数，x=y返回0'''
            return calc_sortval(y)-calc_sortval(x) #权重值大的排前面
        retval.sort(compare)
        retval = retval[:1] #一次返回1个问卷
        #在缓存中记录已发送的问卷
        if cache:
            for x in retval:
                cacher_naire_sent.set(x.QN_ID,fsid)
    return retval

def list_question(qnid):
    '''取问卷题目'''
    retval = dbFrame.select("QN_ITEMS",what="QI_TITLE,QI_OPTION,QI_TYPE",vars=locals(),where="QN_ID=$qnid",order="QI_NO").list()
    for item in retval:
        item['QI_OPTION'] = formatting.json_object(item['QI_OPTION']) #选项json串转成数组
    return retval

def list_0find(fsid,word):
    '''根据关键字从普通问卷标题中模糊查找，最多返回4个问卷。普通问卷：不是自己发的/没有参与过的/正在回收中的/公开调查的'''
    retval = []
    if word:
        word = '%%%s%%'%word
        retval = dbFrame.select("QN_NAIRE N",vars=locals(),where="QN_TITLE like $word AND QN_STATUS=2 AND QN_DEPLOY=1 AND FS_ID!=$fsid AND NOT EXISTS(SELECT * FROM QN_ANSWERS A WHERE A.FS_ID=$fsid AND A.QN_ID=N.QN_ID)",
            order="INSERT_TIME DESC",limit=4).list()
    return retval

def export_naire(qnid):
    '''将问卷基本信息和题目导出成json，不支持图片'''
    QNOBJ = web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="QN_ID=$qnid").list(),0,None)
    if not QNOBJ: return ''
    QNOBJ.pop('STOP_TIME','')
    QNOBJ.pop('NUM_VOTE','')
    QNOBJ.pop('QN_MIN','')
    QNOBJ.pop('END_DATE','')
    QNOBJ.pop('IMG1','')
    QNOBJ.pop('IMG2','')
    QNOBJ.pop('IMGDETAIL','')
    QNOBJ.pop('COMMISSION','')
    QNOBJ.pop('FARE','')
    QNOBJ.pop('TRADE_NO','')
    QNOBJ.pop('PREPAY_ID','')
    QNOBJ.pop('NUM_PAY','')
    QNOBJ.pop('NUM_399001','')
    QNOBJ.pop('WIN_NO','')
    QNOBJ.pop('WIN_SERIAL','')
    QNOBJ.pop('WIN_FSID','')
    QNOBJ.pop('WIN_END','')
    QNOBJ.pop('TOPIC_QNID','')
    QNOBJ.pop('REF_QNID','')
    QNOBJ.pop('SCENE_ID','')
    QNOBJ.pop('QR_TICKET','')
    QNOBJ['items'] = dbFrame.select("QN_ITEMS",vars=locals(),where="QN_ID=$qnid",what="QI_ID,QN_ID,QI_NO,QI_TITLE,QI_TYPE,QI_OPTION").list()
    return formatting.json_string(QNOBJ)

################################################################################
#问卷设置
def set_naire(fsid, qnid, param):
    '''通用的保存问卷基本信息'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        qnid = utils.get_keyword()
    # 将IMG1取出单独保存，并将IMG1字段值设置为图片ID
    img1 = param.pop('IMG1','')
    if img1:
        imgid = QNOBJ.IMG1 if QNOBJ else ''
        retval = set_image(imgid, img1, 1)
        if retval.has_key('error'):
            return retval
        else:
            param['IMG1'] = retval['success']
    t = dbFrame.transaction()
    try:
        if not QNOBJ:
            dbFrame.insert("QN_NAIRE", QN_ID=qnid, FS_ID=fsid, QN_TYPE=-1, INPUT_TIME=utils.get_yyyymmdd(), **param)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", FS_ID=fsid, INPUT_TIME=utils.get_yyyymmdd(), **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if QNOBJ and QNOBJ.WIN_SERIAL: #如果有值说明是复制于某个模板，是先设置题目后设置问卷信息的，跳转至发布预览页面
            return {'success':'predeploy?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        else:
            return {'success':'question?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
def set_qntype(fsid,qnid,qntype):
    '''问卷发布为指定类型，当发布为普通问卷时直接开始回收，其它类型跳转到相应类型的信息录入界面（奖品信息/红包信息/调查币信息）'''
    if qntype.isdigit(): qntype = int(qntype)
    if qntype not in (0,1,2,3):
        return {'error':'无效问卷类型！'}
    if qntype==2: #红包问卷每天不能发超过5个
        yyyymmdd = utils.get_yyyymmdd()
        if web.listget(dbFrame.select("QN_NAIRE",what="COUNT(*) CNT",vars=locals(),where="QN_ID!=$qnid and QN_TYPE=2 and INPUT_TIME=$yyyymmdd").list(),0,{}).get('CNT',0)>=5:
            return {'error':'每天最多只能发5个红包问卷！'}
    t = dbFrame.transaction()
    try:
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", QN_TYPE=qntype)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if qntype==0:
            return deploy_qs(get_naire(qnid))
        elif qntype==1:
            return {'success':'help1_1?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        elif qntype==2:
            return {'success':'help1_2?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        elif qntype==3:
            return {'success':'help1_3?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
def modi_naire(qnid,param):
    '''用于通用的问卷创建后设置各类问卷的相关信息（奖品信息/红包信息/调查币信息）'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    imgdetail = param.pop('IMG3',[])
    if QNOBJ.QN_TYPE==1:
        if not param['PRIZE_VALUE']:
            return {"error":"请输入奖品价值"}
        if param['PRIZE_VALUE'] and not str(param['PRIZE_VALUE']).isdigit():
            return {"error":"请输入奖品价值"}
        param['PRIZE_VALUE'] = int(param['PRIZE_VALUE'])
        if param['PRIZE_VALUE']<=0:
            return {"error":"奖品价值必须大于0元"}
        remove_img3 = param.pop('remove_img3','[]')
        remove_img3 = json.loads(remove_img3) if remove_img3 else []
        param['IMGDETAIL'] = json.loads(QNOBJ.IMGDETAIL) if QNOBJ and QNOBJ.IMGDETAIL else [] #1.取原值或赋空值
        if QNOBJ and QNOBJ.IMGDETAIL and remove_img3:
            retval = del_image(remove_img3)
            if retval.has_key('error'):
                return retval
            param['IMGDETAIL'] = list(set(param['IMGDETAIL']) - set(remove_img3)) #2.移动删除的图片ID
        if imgdetail:
            for imgdata in imgdetail:
                imgid = ''
                retval = set_image(imgid, imgdata, 3)
                if retval.has_key('error'):
                    return retval
                else:
                    param['IMGDETAIL'].append(retval['success']) #3.插入添加的图片ID
        param['IMGDETAIL'] = json.dumps(param['IMGDETAIL']) #4.转成json数组字符串
        # 保存问卷
        param['FARE'] = calc_wxpay_fare(param['PRIZE_VALUE'],1) #计算微信支付手续费
        if not param.get('QN_MAX'):
            param['QN_MAX'] = 0
        param['PRIZE_TITLE'] = param['PRIZE_TITLE'][:64]
    elif QNOBJ.QN_TYPE==2:
        if not param['PRIZE_VALUE']:
            return {"error":"请输入红包金额"}
        if param['PRIZE_VALUE'] and not str(param['PRIZE_VALUE']).isdigit():
            return {"error":"请输入红包金额"}
        param['PRIZE_VALUE'] = int(param['PRIZE_VALUE'])
        if param['PRIZE_VALUE']<=0:
            return {"error":"红包金额必须大于0元"}
        if not param['HONGBAO_NUM']:
            return {"error":"请输入红包个数"}
        if param['HONGBAO_NUM'] and not str(param['HONGBAO_NUM']).isdigit():
            return {"error":"请输入红包个数"}
        param['HONGBAO_NUM'] = int(param['HONGBAO_NUM'])
        if param['HONGBAO_NUM']<=0:
            return {"error":"红包个数必须大于0个"}
        if float(param['PRIZE_VALUE'])/float(param['HONGBAO_NUM'])<0.02:
            return '{"error":"红包金额太小了，请适当增加红包金额或减少红包个数"}'
        param['FARE'] = calc_wxpay_fare(param['PRIZE_VALUE'],2) #计算微信支付手续费
        if param.has_key('HONGBAO_MNY'): #如果是固定金额红包，算出平均值保存在HONGBAO_MNY字段中。否则写0表示拼手气，在用户答卷时计算
            param['HONGBAO_MNY'] = round((float(param['PRIZE_VALUE'])-param['FARE']) / float(param['HONGBAO_NUM']),2)
        else:
            param['HONGBAO_MNY'] = 0
    elif QNOBJ.QN_TYPE==3:
        #互助问卷调查币支付规则：HONGBAO_MNY单份答谢个数，PRIZE_VALUE按目标样本数总计需要个数，NUM_PAY实际支付个数，HONGBAO_SUM累计答谢个数
        #当调查币余额够支付总计个数时正常支付，当不足时用余额全部支付，用户答问卷时到NUM_PAY不足时再看发布人调查币余额补扣。
        #当补扣也不足以支付下一份答谢时自动暂停回收，够支付下一份答谢时就进行补扣，补扣后总支付数未达到PRIZE_VALUE的话就继续补扣
        #发布人答卷、签到等调查币有增加的时候，触发暂停问卷检查程序，如果该用户存在因调查币余额不足而暂停回收的互助问卷，收获调查币后自动恢复回收
        if not param['HONGBAO_MNY']:
            return {"error":"请输入单份回收答谢调查币个数"}
        if param['HONGBAO_MNY'] and not str(param['HONGBAO_MNY']).isdigit():
            return {"error":"请输入单份回收答谢调查币个数"}
        param['HONGBAO_MNY'] = int(param['HONGBAO_MNY'])
        param['PRIZE_VALUE'] = QNOBJ.QN_MAX*param['HONGBAO_MNY']
        FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    t = dbFrame.transaction()
    try:
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return call_wxpay_order(qnid, web.ctx.ip)

def set_nopay(fsid, qnid, param):
    '''保存普通问卷'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        qnid = utils.get_keyword()
    # 将IMG1取出单独保存，并将IMG1字段值设置为图片ID
    img1 = param.pop('IMG1','')
    if img1:
        imgid = QNOBJ.IMG1 if QNOBJ else ''
        retval = set_image(imgid, img1, 1)
        if retval.has_key('error'):
            return retval
        else:
            param['IMG1'] = retval['success']
    t = dbFrame.transaction()
    try:
        if not QNOBJ:
            dbFrame.insert("QN_NAIRE", QN_ID=qnid, FS_ID=fsid, QN_TYPE=0, INPUT_TIME=utils.get_yyyymmdd(), **param)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", FS_ID=fsid, INPUT_TIME=utils.get_yyyymmdd(), **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if QNOBJ and QNOBJ.WIN_SERIAL: #如果有值说明是复制于某个模板，是先设置题目后设置问卷信息的，跳转至发布预览页面
            return {'success':'preview?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        else:
            return {'success':'question?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
def set_hong(fsid, qnid, param):
    '''保存红包问卷'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        qnid = utils.get_keyword()
    # 将IMG1取出单独保存，并将IMG1字段值设置为图片ID
    img1 = param.pop('IMG1','')
    if img1:
        imgid = QNOBJ.IMG1 if QNOBJ else ''
        retval = set_image(imgid, img1, 1)
        if retval.has_key('error'):
            return retval
        else:
            param['IMG1'] = retval['success']
    # 保存问卷
    param['FARE'] = calc_wxpay_fare(param['PRIZE_VALUE'],2) #计算微信支付手续费
    if param.has_key('HONGBAO_MNY'): #如果是固定金额红包，算出平均值保存在HONGBAO_MNY字段中。否则写0表示拼手气，在用户答卷时计算
        param['HONGBAO_MNY'] = round((float(param['PRIZE_VALUE'])-param['FARE']) / float(param['HONGBAO_NUM']),2)
    else:
        param['HONGBAO_MNY'] = 0
    t = dbFrame.transaction()
    try:
        if not QNOBJ:
            dbFrame.insert("QN_NAIRE", QN_ID=qnid, FS_ID=fsid, QN_TYPE=2, INPUT_TIME=utils.get_yyyymmdd(), **param)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", FS_ID=fsid, INPUT_TIME=utils.get_yyyymmdd(), **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if QNOBJ and QNOBJ.WIN_SERIAL: #如果有值说明是复制于某个模板，是先设置题目后设置问卷信息的，跳转至发布预览页面
            return {'success':'preview?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        else:
            return {'success':'question?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
def set_paid(fsid,qnid,param):
    '''保存有奖问卷'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        qnid = utils.get_keyword()
    # 将IMG1，IMG2，IMG3取出单独保存，并将IMG1/IMG2/IMGDETAIL字段值设置为图片ID
    img1 = param.pop('IMG1','')
    if img1:
        imgid = QNOBJ.IMG1 if QNOBJ else ''
        retval = set_image(imgid, img1, 1)
        if retval.has_key('error'):
            return retval
        else:
            param['IMG1'] = retval['success']
    img2 = param.pop('IMG2','')
    if img2:
        imgid = QNOBJ.IMG2 if QNOBJ else ''
        retval = set_image(imgid, img2, 2)
        if retval.has_key('error'):
            return retval
        else:
            param['IMG2'] = retval['success']
    #IMGDETAIL与IMG1/2不同，不是直接编辑，依据remove_img3输入域删除移去的图片，再依据img3域插入添加的图片
    remove_img3 = param.pop('remove_img3','[]')
    remove_img3 = json.loads(remove_img3) if remove_img3 else []
    param['IMGDETAIL'] = json.loads(QNOBJ.IMGDETAIL) if QNOBJ and QNOBJ.IMGDETAIL else [] #1.取原值或赋空值
    if QNOBJ and QNOBJ.IMGDETAIL and remove_img3:
        retval = del_image(remove_img3)
        if retval.has_key('error'):
            return retval
        param['IMGDETAIL'] = list(set(param['IMGDETAIL']) - set(remove_img3)) #2.移动删除的图片ID
    imgdetail = param.pop('IMG3',[])
    if imgdetail:
        for imgdata in imgdetail:
            imgid = ''
            retval = set_image(imgid, imgdata, 3)
            if retval.has_key('error'):
                return retval
            else:
                param['IMGDETAIL'].append(retval['success']) #3.插入添加的图片ID
    param['IMGDETAIL'] = json.dumps(param['IMGDETAIL']) #4.转成json数组字符串
    # 保存问卷
    param['FARE'] = calc_wxpay_fare(param['PRIZE_VALUE'],1) #计算微信支付手续费
    if not param.get('QN_MAX'):
        param['QN_MAX'] = 0
    param['PRIZE_TITLE'] = param['PRIZE_TITLE'][:64]
    t = dbFrame.transaction()
    try:
        if not QNOBJ:
            dbFrame.insert("QN_NAIRE", QN_ID=qnid, FS_ID=fsid, QN_TYPE=1, INPUT_TIME=utils.get_yyyymmdd(), **param)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", FS_ID=fsid, INPUT_TIME=utils.get_yyyymmdd(), **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if QNOBJ and QNOBJ.WIN_SERIAL: #如果有值说明是复制于某个模板，是先设置题目后设置问卷信息的，跳转至发布预览页面
            return {'success':'preview?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
        else:
            return {'success':'question?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}

def set_topic(fsid,tpid,qnid,refqn,param):
    '''保存话题问卷'''
    client_ip = param.pop('client_ip','')
    TPOBJ = get_naire(tpid)
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        qnid = utils.get_keyword()
        param['TRADE_NO'] = utils.get_random_bytime()
    else:
        if QNOBJ.QN_STATUS>=2:
            return {'error':'问卷不允许修改！'}
    FSOBJ = get_fans_byfsid(fsid)
    # 问卷基本信息
    if param['PRIZE_VALUE'] and str(param['PRIZE_VALUE']).isdigit() and float(param['PRIZE_VALUE'])>0: #如果有红包金额就设置为红包问卷
        param['PRIZE_VALUE'] = float(param['PRIZE_VALUE'])
        qntype = 2
        param['FARE'] = calc_wxpay_fare(param['PRIZE_VALUE'],qntype)  #计算微信支付手续费
        if param.has_key('HONGBAO_MNY'): #如果是固定金额红包，算出平均值保存在HONGBAO_MNY字段中。否则写0表示拼手气，在用户答卷时计算
            param['HONGBAO_MNY'] = round((param['PRIZE_VALUE']-param['FARE']) / float(param['HONGBAO_NUM']),2)
        else:
            param['HONGBAO_MNY'] = 0
    else:
        qntype = 0
    #从话题模板复制IMG1和IMG2
    param['IMG1'] = TPOBJ.IMG1 if TPOBJ and TPOBJ.IMG1 else None
    param['IMG2'] = TPOBJ.IMG2 if TPOBJ and TPOBJ.IMG2 else None
    # 保存问卷
    t = dbFrame.transaction()
    try:
        if not QNOBJ:
            allitem = dbFrame.select("QN_ITEMS",vars=locals(),where="QN_ID=$tpid").list()
            if refqn and not web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="REF_QNID=$refqn and FS_ID=$fsid").list(),0,None):
                #发话题问卷只能引用一次，否则有无限制补发红包漏洞
                param['REF_QNID'] = refqn
            dbFrame.insert("QN_NAIRE", QN_ID=qnid, FS_ID=fsid, QN_TYPE=qntype, QN_NO=len(allitem), TOPIC_QNID=tpid, INPUT_TIME=utils.get_yyyymmdd(), **param)
            for item in allitem:
                item.pop('QI_ID','')
                item.pop('QN_ID','')
                dbFrame.insert("QN_ITEMS",QI_ID=utils.get_keyword(),QN_ID=qnid,**item)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", FS_ID=fsid, QN_TYPE=qntype, TOPIC_QNID=tpid, INPUT_TIME=utils.get_yyyymmdd(), **param)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        #话题问卷创建完成，调用下单接口（需要支付的问卷转去支付页面，不需要支付的直接发布转到完成页面）
        return call_wxpay_order(qnid,client_ip)
        #话题问卷创建完成，不设置题目，直接进入预览页面
        # return {'success':'preview?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}

def create_qs(fsid,tpid,qntype,allitem,refqn):
    '''复刻指定模板创建新问卷'''
    TPOBJ = get_naire(tpid)
    if not TPOBJ:
        return {'error':'无效的问卷模板！'}
    t = dbFrame.transaction()
    try:
        allitem = json.loads(allitem)
        qnid = utils.get_keyword()
        data = {'FS_ID':fsid, 'QN_TYPE':qntype, 'QN_TITLE':TPOBJ.QN_TITLE, 'QN_NO':len(allitem), 'IMG1':TPOBJ.IMG1, 'IMG2':TPOBJ.IMG2, 'WIN_SERIAL':tpid, 'INPUT_TIME':utils.get_yyyymmdd()}
        if TPOBJ.QN_STATUS==99: #发话题问卷
            data['QN_SUMMARY'] = TPOBJ.PRIZE_TITLE if TPOBJ.PRIZE_TITLE else ''
            data['TOPIC_QNID'] = tpid
            data['QN_PUBLIC'] = 1
            if refqn and not web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="REF_QNID=$refqn and FS_ID=$fsid").list(),0,None):
                #发话题问卷只能引用一次，否则有无限制补发红包漏洞
                data['REF_QNID'] = refqn
        dbFrame.insert("QN_NAIRE",QN_ID=qnid,**data)
        for no, item in enumerate(allitem,1):
            item['QI_OPTION'] = formatting.json_string(item['QI_OPTION'],ensure_ascii=False) #选项数组转成json串
            dbFrame.insert("QN_ITEMS",QI_ID=utils.get_keyword(),QN_ID=qnid,QI_NO=no,**item)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        seeurl = 'createqs'
        return {'success':seeurl+'?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}


def del_qsnaire(fsid,qnid):
    '''删除问卷。只有编辑中的问卷才可以删除'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    if str(QNOBJ.FS_ID)!=str(fsid):
        return {'error':'只有问卷创建人能删除问卷！'}
    if QNOBJ.QN_STATUS>=2:
        return {'error':'已发布问卷不能删除'}
    t = dbFrame.transaction()
    try:
        dbFrame.delete("QN_ITEMS",vars=locals(),where="QN_ID=$qnid")
        dbFrame.delete("QN_NAIRE",vars=locals(),where="QN_ID=$qnid")
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':qnid}


################################################################################
#问卷题目管理
def set_question(fsid,qnid,allitem):
    '''设置问卷题目。先删除再添加方式'''
    t = dbFrame.transaction()
    try:
        allitem = json.loads(allitem)
        dbFrame.delete("QN_ITEMS",vars=locals(),where="QN_ID=$qnid")
        no = 1
        for item in allitem:
            item['QI_OPTION'] = formatting.json_string(item['QI_OPTION'],ensure_ascii=False) #选项数组转成json串
            dbFrame.insert("QN_ITEMS",QI_ID=utils.get_keyword(),QN_ID=qnid,QI_NO=no,**item)
            no += 1
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", QN_NO=no-1)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':'predeploy?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))}
def add_question(qnid,addqis):
    '''向问卷添加题目，传入addqis为题目编号数组，将这些题目复制一份添加到指定问卷'''
    addqis = json.loads(addqis)
    allitem = dbFrame.select("QN_ITEMS",vars=locals(),where="QI_ID in $addqis",order="QN_ID,QI_NO").list()
    QNOBJ = get_naire(qnid)
    t = dbFrame.transaction()
    try:
        no = QNOBJ.QN_NO+1 if QNOBJ.QN_NO else 1
        for item in allitem:
            item.pop('QI_ID')
            item.pop('QN_ID')
            item.pop('QI_NO')
            item.pop('QI_ANSTAT')
            dbFrame.insert("QN_ITEMS",QI_ID=utils.get_keyword(),QN_ID=qnid,QI_NO=no,**item)
            no += 1
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", QN_NO=no-1)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':len(allitem)}

################################################################################
#微信支付
def call_wxpay_order(qnid,client_ip):
    '''统一下单。所有问卷都通过此接口进行下单，需要支付的问卷转去支付页面，不需要支付的问卷直接调用发布接口发布'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    if wxcode!='test' and QNOBJ.QN_TYPE in (1,2): #测试号不跳转到支付界面而是直接发布
        if QNOBJ.QN_TYPE==1:
            title = '有奖问卷-履行兑奖保证金'
            fee = QNOBJ.PRIZE_VALUE + QNOBJ.FARE
            seeurl = '/jsapi/paid2'
        elif QNOBJ.QN_TYPE==2:
            title = '红包问卷-红包款'
            fee = QNOBJ.PRIZE_VALUE
            seeurl = '/jsapi/hong2'
    elif QNOBJ.QN_TYPE==3:
        title = '互助问卷-调查币'
        fee = QNOBJ.PRIZE_VALUE
        seeurl = '/jsapi/help2'
    else:
        return deploy_qs(QNOBJ)
    retval = {'success':seeurl+'?fsid=%s&r=%s&qnid=%s'%(str(QNOBJ.FS_ID),cacher_random_checker.genRandomValueForFSID(QNOBJ.FS_ID),str(qnid))}
    if QNOBJ.QN_TYPE==3:
        return retval
    #不能使用之前下的单，金额改过的话使用之前下的单就还是原来的金额
    # if isValidPrepayID(QNOBJ.PREPAY_ID):
    #     return retval #已经生成过统一支付订单了
    tradeno = utils.get_random_bytime()
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    import mforweixin
    retdat = mforweixin.wxpay_unifiedorder(title,tradeno,fee,client_ip,FSOBJ.OPENID)
    if retdat.has_key('success'):
        prepayid = retdat['success']
        t = dbFrame.transaction()
        try:
            #删除之前的未完成的订单
            if QNOBJ.TRADE_NO:
                dbFrame.delete("QN_WXPAYINCOME",vars=locals(),where="TRADE_NO=$QNOBJ.TRADE_NO")
            #保存新的商户订单号和统一下单号
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", TRADE_NO=tradeno, PREPAY_ID=prepayid)
            if QNOBJ.QN_TYPE==2:
                dbFrame.insert("QN_WXPAYINCOME", TRADE_NO=tradeno, SHOULD_PAY=float(QNOBJ['PRIZE_VALUE']))
            elif QNOBJ.QN_TYPE==1:
                dbFrame.insert("QN_WXPAYINCOME", TRADE_NO=tradeno, SHOULD_PAY=float(QNOBJ['PRIZE_VALUE'])+float(QNOBJ['FARE']))
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':e}
        else:
            t.commit()
            return retval
    else:
        return {'error':retdat['error']}
def set_wxpay_resp(data):
    '''保存微信支付成功，从报文中解析出trade_no确定是哪个问卷的'''
    tradeno = data.get('out_trade_no','')
    if not tradeno:
        return {'error':'微信支付通知空订单号'}
    m = web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="TRADE_NO=$tradeno").list(),0,None)
    if not m:
        return {'error':'微信支付通知订单号不能识别'}
    t = dbFrame.transaction()
    try:
        dbFrame.update("QN_NAIRE",vars=locals(),where="TRADE_NO=$tradeno", NUM_PAY=float(data['total_fee'])/100)
        dbFrame.update("QN_WXPAYINCOME",vars=locals(),where="TRADE_NO=$tradeno", FACT_PAY=float(data['total_fee'])/100, TRANSACTION_ID=data['transaction_id'], TIME_END=data['time_end'], PAY_RESP=formatting.json_string(data))
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':tradeno}
def check_wxpay_resp(qnid):
    '''检查问卷是否已支付'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    return deploy_qs(QNOBJ)

def get_hongbao_cache(fsid):
    '''取用户缓存中未发放的红包总金额'''
    m = dbFrame.select("QN_REDCACHE",what="FS_ID,SUMMARY,CC_HONGBAO",vars=locals(),where="FS_ID=$fsid",order="INPUT_TIME").list()
    detail = []
    retval = 0
    for x in m:
        detail.append(u'%s:%s:%s'%(x.FS_ID, x.SUMMARY, x.CC_HONGBAO))
        retval += round(float(x.CC_HONGBAO),2) or 0
    if detail:
        detail.append(u'总额：%.2f'%retval)
    return retval, u'\n'.join(detail)
def check_wxpay_hong_and_send(fsid):
    '''检查指定用户的累计未发红包金额，如果大于1元就可以发放红包'''
    FSOBJ = get_fans_byfsid(fsid)
    t = dbFrame.transaction()
    try:
        hongbaototal, hongbaodetail = get_hongbao_cache(fsid)
        needsend = hongbaototal
        if needsend>=1:
            dbFrame.query("INSERT INTO QNHIS_REDCACHE_MAIN SELECT * FROM QN_REDCACHE WHERE FS_ID="+str(fsid))
            dbFrame.delete("QN_REDCACHE",vars=locals(),where="FS_ID=$fsid")
            import mqsnaire, madmin
            #大于1元时才发放。如果大于200，按单次200循环发放
            while needsend>=1:
                amount = 200 if needsend>200 else needsend
                needsend = needsend-amount
                billno = utils.get_time18()
                dbFrame.insert("QN_REDSERIAL",RS_ID=utils.get_keyword(),FS_ID=fsid,OPENID=FSOBJ.OPENID,BILL_NO=billno,PAY_HONGBAO=amount,INPUT_TIME=utils.get_yyyymmddhhmmssFromString(utils.get_currdatetimestr(dbFrame.dbtype)))
                if wxcode!='test': #测试号不发红包
                    madmin.sendToMe('%s: %.2f'%(fsid,amount))
                    mqsnaire.sendredpack(FSOBJ.OPENID,amount,billno) #这个是延时异步执行的，所以不检查返回
            if needsend>0: #剩余不足1元的保存下来
                dbFrame.insert("QN_REDCACHE",CC_ID=utils.get_keyword(),OPENID=FSOBJ.OPENID,FS_ID=fsid,QN_ID='surplus',AN_ID='surplus',CC_HONGBAO=needsend,SUMMARY='结余')
            madmin.sendToMe(hongbaodetail) #给我自己发送发红包通知（但是否成功并不知道）
        dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$fsid",NOTPAY_A2=needsend)
        # cacher_fans_obj.delete(fsid)
        FSOBJ.update({'NOTPAY_A2':needsend}) #更新缓存
        cacher_fans_obj.set(fsid,FSOBJ)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':hongbaototal}

def set_wxpay_hong(data):
    '''保存微信红包发送成功结果'''
    billno = data.get('mch_billno','')
    mchid = data.get('mch_id','')
    billno = billno.replace(mchid,'')
    m = web.listget(dbFrame.select("QN_REDSERIAL",vars=locals(),where="BILL_NO=$billno").list(),0,None)
    import madmin
    if not m:
        madmin.sendToMe(u'%s: %s'%(billno,u'微信支付红包订单号不能识别'))
        return {'error':'微信支付红包订单号不能识别'}
    else:
        madmin.sendToMe(u'%s: %s'%(billno,data['total_amount']))
    t = dbFrame.transaction()
    try:
        dbFrame.update("QN_REDSERIAL",vars=locals(),where="BILL_NO=$billno", FCT_HONGBAO=float(data['total_amount'])/100, RESP_PAYRED=formatting.json_string(data))
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':billno}

################################################################################
#问卷发布/暂停/停止
def deploy_qs(QNOBJ):
    '''问卷开始回收'''
    if not QNOBJ.QN_NO:
        return {'error':'问卷还没有添加题目！'}
    qnid = QNOBJ.QN_ID
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    savedata = {"QN_STATUS":2, "INPUT_TIME":utils.get_yyyymmdd()}
    if wxcode!='test' and QNOBJ.QN_TYPE in (1,2,): #测试号不检查已付款金额
        if QNOBJ.QN_TYPE==1 and ((QNOBJ.NUM_PAY and QNOBJ.NUM_PAY<(QNOBJ.PRIZE_VALUE+QNOBJ.FARE)) or not QNOBJ.NUM_PAY):
            return {'error':'有奖问卷需要预付保证金后才能开始回收'}
        if QNOBJ.QN_TYPE==2 and ((QNOBJ.NUM_PAY and QNOBJ.NUM_PAY<QNOBJ.PRIZE_VALUE) or not QNOBJ.NUM_PAY):
            return {'error':'红包问卷需要支付后才能开始回收'}
    elif QNOBJ.QN_TYPE==3 and ((QNOBJ.NUM_PAY and QNOBJ.NUM_PAY<QNOBJ.PRIZE_VALUE) or not QNOBJ.NUM_PAY):
        #支付调查币不需要调用微信支付，因此不需要相应支付和接收微信支付结果环节，在验证并发布时直接做调查币扣除，等价于先做支付验证再发布
        factpay = min(FSOBJ.COIN_HOLD,QNOBJ.PRIZE_VALUE-(QNOBJ.NUM_PAY if QNOBJ.NUM_PAY else 0))
        if factpay<QNOBJ.HONGBAO_MNY: #如果实际支付调查币不够一份答谢，直接暂停问卷
            savedata['QN_STATUS'] = 3
        t = dbFrame.transaction()
        try:
            retdat = set_fans_coin(FSOBJ, -factpay, 21, '发问卷')
            prepayid = retdat.get('success','')
            if prepayid:
                dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid", TRADE_NO=utils.get_random_bytime(), PREPAY_ID=prepayid, NUM_PAY=factpay)
            else:
                raise Exception(retdat.get('error',''))
        except Exception, e:
            t.rollback()
            return {'error':str(e)}
        else:
            t.commit()
    hongbao1 = 0
    t = dbFrame.transaction()
    try:
        dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$qnid",**savedata)
        retval = add_fans_count(QNOBJ.FS_ID,'COUNT_P%d'%QNOBJ.QN_TYPE)
        if retval:
            raise Exception(retval)
        #发话题问卷并且是从别的话题问卷引荐而发的，需要补发红包，红包款从引荐他的那个话题问卷出，发剩下的30%
        if QNOBJ.TOPIC_QNID and QNOBJ.REF_QNID:
            ANOBJ = web.listget(dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$QNOBJ.REF_QNID AND FS_ID=$QNOBJ.FS_ID").list(),0,None)
            if ANOBJ: #如果当前发布问卷用户确实参与了引荐话题问卷，那么是要给他补发红包的
                hongbao1 = float(calc_hongbao(get_naire(QNOBJ.REF_QNID),None,True))
                if hongbao1>0:
                    #需要登记发红包缓存，更新问卷表累计发放红包金额，更新该用户对应的回答记录的红包金额，更新用户累计抢到红包金额
                    dbFrame.insert("QN_REDCACHE",CC_ID=utils.get_keyword(),OPENID=FSOBJ.OPENID,FS_ID=FSOBJ.FS_ID,QN_ID=QNOBJ.REF_QNID,AN_ID='additional',CC_HONGBAO=hongbao1,SUMMARY='发话题问卷')
                    dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$QNOBJ.REF_QNID",HONGBAO_SUM=web.SQLLiteral("HONGBAO_SUM+"+str(hongbao1)))
                    dbFrame.update('QN_ANSWERS',vars=locals(),where="QN_ID=$QNOBJ.REF_QNID AND FS_ID=$QNOBJ.FS_ID",AN_HONGBAO=web.SQLLiteral("AN_HONGBAO+"+str(hongbao1)))
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
    if hongbao1>0: #发话题问卷并且是从别的话题问卷引荐而发的，需要补发红包，红包款从引荐他的那个话题问卷出。金额大于0时尝试发红包
        add_fans_count(FSOBJ.FS_ID, 'SUM_A2', hongbao1)
        retmsg = u'发话题问卷获得 %.2f 元红包'%hongbao1
        retdat = check_wxpay_hong_and_send(QNOBJ.FS_ID)
        if retdat.has_key('success'):
            hongbao1 = retdat['success']
            if hongbao1>=1:
                retmsg += u'。累计需要发放 %.2f 元，请注意查收'%hongbao1
            else:
                retmsg += u'。累计需要发放 %.2f 元，由于微信平台商户向粉丝发放红包金额限制，需要累计达到1元，届时会自动发放'%hongbao1
        cacher_message_pool.set(QNOBJ.FS_ID,retmsg)
    sendDeployMessage(QNOBJ)
    if QNOBJ.QN_TYPE==0:
        seeurl = '/nopay3'
    elif QNOBJ.QN_TYPE==1:
        seeurl = '/paid3'
    elif QNOBJ.QN_TYPE==2:
        seeurl = '/hong3'
    elif QNOBJ.QN_TYPE==3:
        seeurl = '/help3'
    return {'success':seeurl+'?fsid=%s&r=%s&qnid=%s'%(str(QNOBJ.FS_ID),cacher_random_checker.genRandomValueForFSID(QNOBJ.FS_ID),str(qnid))}
def pause_qs(qnid):
    '''问卷暂停回收'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    t = dbFrame.transaction()
    try:
        savedata = {"QN_STATUS":3}
        dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$qnid",**savedata)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':qnid}
def resume_qs(qnid):
    '''问卷恢复回收'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    #非互助问卷，或者互助问卷是部分付款且发卷人当前调查币余额已够答谢下次答卷
    if QNOBJ.QN_TYPE!=3 or (QNOBJ.QN_TYPE==3 and QNOBJ.PRIZE_VALUE>QNOBJ.NUM_PAY and FSOBJ.COIN_HOLD>QNOBJ.HONGBAO_MNY):
        t = dbFrame.transaction()
        try:
            savedata = {"QN_STATUS":2}
            dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$qnid",**savedata)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':e}
        else:
            t.commit()
            return {'success':qnid}
    else:
        if QNOBJ.PRIZE_VALUE<=QNOBJ.NUM_PAY:
            return {'error':'问卷已达到目标回收样本数，请停止回收'}
        else:
            return {'error':'调查币余额不够补扣，不能恢复回收此问卷'}
def stop_qs(qnid):
    '''问卷停止回收'''
    QNOBJ = get_naire(qnid)
    if not QNOBJ:
        return {'error':'问卷不存在！'}
    if QNOBJ.QN_STATUS not in (2,3):
        return {'error':'问卷已经停止回收了！'}
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    retmsg = '问卷已停止回收'
    t = dbFrame.transaction()
    try:
        savedata = {"QN_STATUS":9,"STOP_TIME":utils.get_currdatetimestr(dbFrame.dbtype)}
        if QNOBJ.QN_TYPE==0:
            savedata['WIN_END'] = 2
        elif QNOBJ.QN_TYPE==1:
            retmsg += '。抽奖会在最近一个深交所交易日收盘后进行，届时关注抽奖结果'
        elif QNOBJ.QN_TYPE==2:
            savedata['END_DATE'] = datetime.datetime.today().strftime("%Y%m%d")
            savedata['WIN_END'] = 2
            backval = round(float(QNOBJ.PRIZE_VALUE)-float(QNOBJ.FARE)-float(QNOBJ.HONGBAO_SUM),2) #红包剩余金额
            if backval>0:
                retmsg += '。红包剩余金额 %.2f 即将退回，请注意查收。'%(backval)
                if not dbFrame.select("QN_REDCACHE",vars=dict(anid='back'+qnid),where="AN_ID=$anid").list() and not dbFrame.select("QNHIS_REDCACHE_MAIN",vars=dict(anid='back'+qnid),where="AN_ID=$anid").list():
                    dbFrame.insert("QN_REDCACHE",CC_ID=utils.get_keyword(),OPENID=FSOBJ.OPENID,FS_ID=QNOBJ.FS_ID,QN_ID=QNOBJ.QN_ID,AN_ID='back'+qnid,CC_HONGBAO=backval,SUMMARY='剩余红包退回')
            else:
                retmsg += '。红包已被抢光，没有剩余金额需要退回。'
        elif QNOBJ.QN_TYPE==3:
            savedata['WIN_END'] = 2
            backval = round(float(QNOBJ.NUM_PAY) - float(QNOBJ.HONGBAO_SUM), 0)
            if backval>0: #互助问卷结束时剩余调查币退回
                dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=QNOBJ.FS_ID,CHG_TYPE=19,CHG_AMOUNT=backval,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype))
                dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$QNOBJ.FS_ID",COIN_TOTAL=web.SQLLiteral("COIN_TOTAL+%d"%backval),COIN_HOLD=web.SQLLiteral("COIN_HOLD+%d"%backval) )
                FSOBJ.COIN_HOLD = FSOBJ.COIN_HOLD+backval
                cacher_fans_obj.set(FSOBJ.FS_ID,FSOBJ) #更新缓存
                check_pause_naire3(FSOBJ)
        dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$qnid",**savedata)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        if QNOBJ.QN_TYPE==2 and backval>0:
            check_wxpay_hong_and_send(FSOBJ.FS_ID)
        return {'success':retmsg}

def sendDeployMessage(QNOBJ):
    '''向问卷发布人发送问卷发布成功通知。传入问卷对象'''
    import mqsnaire
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    #文本消息告知问卷已发布成功
    if canSendServiceMessage(FSOBJ):
        mqsnaire.sendDeploySuccessMessage(FSOBJ.OPENID,QNOBJ)


################################################################################
#答卷相关
def get_answer(qnid,fsid):
    '''获取问卷参与数据'''
    return web.listget(dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid and FS_ID=$fsid").list(),0,None)
def append_anshint(FSOBJ,QNOBJ):
    retmsg = u''
    if QNOBJ.QN_PUBLIC==1:
        retmsg += u'<br>你可以<a href="/stview?fsid=%s&r=%s&qnid=%s">查看问卷统计结果</a>'%(FSOBJ.FS_ID,cacher_random_checker.genRandomValueForFSID(FSOBJ.FS_ID),QNOBJ.QN_ID)
    #答完卷以后提示，分几种情况：
    #1.未关注的用户提示关注。关注后有更多有奖问卷和红包问卷。
    #2.如果答的是话题问卷。提示也发一个。
    if QNOBJ.TOPIC_QNID: #如果是一个话题问卷
        TPOBJ = get_naire(QNOBJ.TOPIC_QNID)
        retmsg += u'<br><br>%s<br><strong style="color:red;"><a href="/topic1?fsid=%s&r=%s&tpid=%s&refqn=%s">现在创建</a>还可以再拿到一个红包呦！</strong><br>现在不想创建？那就分享给朋友发个福利吧！'%(TPOBJ.QN_SUMMARY,FSOBJ.FS_ID,cacher_random_checker.genRandomValueForFSID(FSOBJ.FS_ID),QNOBJ.TOPIC_QNID,QNOBJ.QN_ID)
    canans = list_cananswer(FSOBJ.FS_ID,2,False)
    #不管有没有关注，给一个有奖问卷二维码，可识别参与。如果没有可参与的有奖问卷的话，再判断未关注的提醒关注
    if canans:
        qrimg = u'https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket='+canans[0].QR_TICKET
        if canans[0].QN_TYPE==1:
            title = u'给您推荐<strong style="color:red;">有奖调查问卷</strong>：%s'%canans[0]['QN_TITLE']
            desc = u'<strong style="color:red;">%s</strong>'%canans[0]['SHARE_DESC'].decode('utf8')
            retmsg += u'<br>%s<br>%s<br>长按并识别下方二维码即可参与<br><img width="50%%" src="%s">'%(title,desc,qrimg)
        elif canans[0].QN_TYPE==2:
            title = u'给您推荐<strong style="color:red;">红包调查问卷：%s</strong>'%canans[0]['QN_TITLE']
            if canans[0].HONGBAO_MNY>0:
                desc = u'答问卷可得 %.2f 元红包，先到先得'%round(float(canans[0].HONGBAO_MNY),2)
            else:
                desc = u'答问卷可得约 %.2f 元红包，先到先得'%round(float(canans[0].PRIZE_VALUE)/float(canans[0].HONGBAO_NUM),2)
            retmsg += u'<br>%s<br>%s<br>长按并识别下方二维码即可参与<br><img width="50%%" src="%s">'%(title,desc,qrimg)
    else:
        if not FSOBJ.SUBSCRIBE:
            # if QNOBJ.QR_TICKET: #如果问卷有二维码，给问卷二维码关注
            #     qrimg = u'https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket='+QNOBJ.QR_TICKET
            # else:
            qrimg = u'/static/img/qrcode_diaochadashi.jpg'
            retmsg += u'<br><img width="50%%" src="%s"><br>关注【问卷调查大师】<strong style="color:red;">抢更多奖品和红包</strong><br>长按并识别上方二维码即可关注'%qrimg
    return retmsg
def get_anshint(FSOBJ,QNOBJ,ANOBJ):
    '''根据问卷对象和fsid判断是否已参与该问卷，已参与的返回参与问卷提示消息，未参与的返回None'''
    retval = u''
    if ANOBJ:
        if QNOBJ.QN_TYPE==1:
            retval = u'你已参与过此问卷，你的抽奖号 %d'%ANOBJ.ANSWER_NO
        elif QNOBJ.QN_TYPE==2:
            retval = u'你已参与过此问卷，抢到 %.2f 元红包'%ANOBJ.AN_HONGBAO
        elif QNOBJ.QN_TYPE==3:
            retval = u'你已参与过此问卷，获得答谢 %.0f 调查币，获得奖励 %.0f 调查币'%(ANOBJ.AN_HONGBAO,ANOBJ.AN_JIANGLI)
        else:
            retval = u'你已参与过此问卷'
        retval += append_anshint(FSOBJ,QNOBJ)
    return retval
def calc_hongbao(QNOBJ,ANOBJ,deliver=False):
    '''传入问卷对象、答案对象，计算单个红包金额。deliver用来传递发话题问卷时计算剩下的红包。返回：单个红包金额'''
    ret1 = 0
    if QNOBJ and QNOBJ.QN_TYPE==2 and QNOBJ.HONGBAO_NUM:
        #如果已参与过问卷，取当时计算的发放红包金额，不再重新计算
        if ANOBJ:
            ret1 = float(ANOBJ.AN_HONGBAO)
        else:
            #取累计已发红包金额，已发个数，得到剩余金额
            anid = ANOBJ.AN_ID if ANOBJ else ''
            m = web.listget(dbFrame.select("QN_ANSWERS",what="SUM(AN_HONGBAO) AN_HONGBAO, COUNT(*) CNT",vars=locals(),where="QN_ID=$QNOBJ.QN_ID AND AN_ID!=$anid AND AN_HONGBAO>0").list(),0,None)
            total = float(m.AN_HONGBAO) if m and m.AN_HONGBAO else 0
            count = QNOBJ.HONGBAO_NUM - (m.CNT if m else 0) #总数-累计已发个数（QN_ANSWERS中该问卷答案中红包金额不为0的个数）
            left = round((float(QNOBJ.PRIZE_VALUE)-float(QNOBJ.FARE))-total,2) #剩余红包金额
            #生成本次红包金额
            if QNOBJ.HONGBAO_MNY:
                #固定单个红包金额
                ret1 = float(QNOBJ.HONGBAO_MNY)
            else:
                #随机计算单个红包金额，在平均金额的基础上，上下浮动100%
                if count<=0:
                    base = 0
                else:
                    base = round(left / count, 2)
                import random
                ret1 = round(base+(base*random.uniform(-1,1)),2)
            #最后校正一下金额，保证不超发
            if count<=1:
                ret1 = left #如果只剩一个红包，剩余金额全给他
            else:
                ret1 = min(left,ret1) #取小的值，确保本次发红包金额不会超出剩余红包金额
            if QNOBJ.TOPIC_QNID: #如果是参与话题问卷，红包发70%，剩下30%他传递创建话题问卷时发
                if not deliver:
                    ret1 = round(ret1*0.7,2)
                else:
                    ret1 = round(ret1*0.3,2)
    return ret1
def check_thanks_coin(QNOBJ):
    '''用于互助问卷，检查答谢币总额、已付、余额。返回本次答卷的答谢币。本函数在set_answer中调用，修改表数据时不使用事务'''
    retval = 0
    if not QNOBJ.NUM_PAY:
        return round(retval,0)
    FSOBJ = get_fans_byfsid(QNOBJ.FS_ID)
    if QNOBJ.NUM_PAY<QNOBJ.PRIZE_VALUE and QNOBJ.NUM_PAY-QNOBJ.HONGBAO_SUM<2*QNOBJ.HONGBAO_MNY: #未全额支付调查币，且不够答谢下次答卷，尝试补扣
        needcoin = QNOBJ.PRIZE_VALUE-QNOBJ.NUM_PAY if QNOBJ.PRIZE_VALUE>QNOBJ.NUM_PAY else 0 #需要补扣数
        canpay = int(round(min(FSOBJ.COIN_HOLD,needcoin),0)) #实际补扣数
        if canpay>0: #修改：问卷表实付调查币，发卷人调查币流水，发卷人调查币余额。修改：变量值
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$QNOBJ.QN_ID",NUM_PAY=web.SQLLiteral("NUM_PAY+%d"%canpay))
            dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=QNOBJ.FS_ID,CHG_TYPE=22,CHG_AMOUNT=-canpay,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype))
            dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$QNOBJ.FS_ID",COIN_HOLD=web.SQLLiteral("COIN_HOLD-%d"%canpay))
            QNOBJ.NUM_PAY = QNOBJ.NUM_PAY+canpay
            FSOBJ.COIN_HOLD = FSOBJ.COIN_HOLD-canpay
            cacher_fans_obj.set(FSOBJ.FS_ID,FSOBJ) #更新缓存
    if QNOBJ.NUM_PAY-QNOBJ.HONGBAO_SUM<2*QNOBJ.HONGBAO_MNY: #不够答谢下次答卷，暂停问卷
        if QNOBJ.NUM_VOTE+1>=QNOBJ.QN_MAX: #本次答卷后达到目标样本数，自动停止回收
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$QNOBJ.QN_ID",QN_STATUS=9)
        else:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$QNOBJ.QN_ID",QN_STATUS=3)
    #不够答谢本次答卷(未全额支付)，或预计样本已达到(已全额支付)，本次答谢0调查币，并暂停问卷(上面不够答谢下次答卷的判断已经暂停问卷了，不用再重复暂停)
    if QNOBJ.NUM_PAY-QNOBJ.HONGBAO_SUM<QNOBJ.HONGBAO_MNY:
        retval = 0
    else: #已付调查币够答谢本次答卷（还未达到目标样本）
        retval = QNOBJ.HONGBAO_MNY
    return round(retval,0)
def check_pause_naire3(FSOBJ):
    '''用于用户收入调查币时，检查用户是否有暂停的互助问卷，收入调查币后是否足够支持问卷自动恢复回收，若支持就自动恢复回收'''
    #本函数在用户有收放调查币时（修改WX_FANS的调查币字段后，且更新了FSOBJ后）调用，修改表数据时不使用事务
    #取1个可恢复回收的互助问卷
    QN = web.listget(dbFrame.select("QN_NAIRE",vars=locals(),where="QN_TYPE=3 AND QN_STATUS=3 AND HONGBAO_MNY<$FSOBJ.COIN_HOLD").list(),0,None)
    if QN:
        needcoin = QN.PRIZE_VALUE-QN.NUM_PAY if QN.PRIZE_VALUE>QN.NUM_PAY else 0 #需要补扣数
        canpay = int(round(min(FSOBJ.COIN_HOLD,needcoin),0)) #能补扣数
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$QN.QN_ID",NUM_PAY=web.SQLLiteral("NUM_PAY+%d"%canpay),QN_STATUS=2)
        dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=QN.FS_ID,CHG_TYPE=22,CHG_AMOUNT=-canpay,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype))
        dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$QN.FS_ID",COIN_HOLD=web.SQLLiteral("COIN_HOLD-%d"%canpay))
        FSOBJ.COIN_HOLD = FSOBJ.COIN_HOLD-canpay
        cacher_fans_obj.set(FSOBJ.FS_ID,FSOBJ) #更新缓存

def set_answer(qnid,fsid,content,clientip):
    '''保存问卷回答'''
    QNOBJ = get_naire(qnid)
    FSOBJ = get_fans_byfsid(fsid)
    ANOBJ = get_answer(qnid,fsid)
    anshint = get_anshint(FSOBJ,QNOBJ,ANOBJ)
    if anshint:
        return {'error':anshint}
    hongbao1 = float(calc_hongbao(QNOBJ,ANOBJ))
    coinjiangli = 0
    if not ANOBJ: #如果重复答卷什么都不干
        t = dbFrame.transaction()
        try:
            bNeedReloadQNItems = False
            qitems = dbFrame.select('QN_ITEMS',vars=locals(),where="QN_ID=$qnid",order="QI_NO").list()
            #文字类问题先检查更新QN_ITEMS的QI_OPTION，然后修改答案中的文本为序号
            for idx,item in enumerate(qitems):
                if item.QI_TYPE=='T':
                    bNeedReloadQNItems = True
                    qiop = json.loads(item.QI_OPTION) if item.QI_OPTION else []
                    content = json.loads(content)
                    ans = content[idx]
                    if ans not in qiop:
                        content[idx] = len(qiop)
                        content = json.dumps(content)
                        qiop.append(ans)
                        if item.QI_ANSTAT: #如果已有统计结果需要在结果中添加新选项的统计计数
                            anstat = json.loads(item.QI_ANSTAT)
                            anstat.append(0)
                        else:
                            anstat = None
                        dbFrame.update("QN_ITEMS",vars=locals(),where="QN_ID=$qnid and QI_NO=$item.QI_NO",QI_OPTION=json.dumps(qiop,ensure_ascii=False),QI_ANSTAT=json.dumps(anstat,ensure_ascii=False) if anstat else None)
                    else:
                        content[idx] = qiop.index(ans)
                        content = json.dumps(content)
            if bNeedReloadQNItems:
                qitems = dbFrame.select('QN_ITEMS',vars=locals(),where="QN_ID=$qnid",order="QI_NO").list()
            #为引荐人分配一个抽奖号
            annos = generateLotteryNo(QNOBJ, FSOBJ)
            if len(annos)==2: #有2个抽奖号说明第2个是给引荐人的
                inby = FSOBJ.IN_BY if FSOBJ.IN_BY else 10000
                dbFrame.insert('QN_LOTTERY',LT_ID=utils.get_keyword(),QN_ID=qnid,FS_ID=inby,LOTTERY_NO=annos[1])
            anid = utils.get_keyword()
            anno = annos[0] if len(annos)>0 else 0
            #互助问卷处理答谢调查币
            cointhanks = 0
            if QNOBJ.QN_TYPE==3:
                #如果已支付调查币-累计实付调查币>单份答卷答谢调查币，则答谢调查币设置为预设值，否则设置为0。已支付调查币-累计实付调查币不足以支付下份答谢时自动补扣，余额不足以补扣时自动暂停回收
                cointhanks = check_thanks_coin(QNOBJ)
                hongbao1 = cointhanks #把答谢调查币保存到AN_HONGBAO中，把奖励调查币保存到AN_JIANGLI字段中
                dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,CHG_TYPE=14,CHG_AMOUNT=cointhanks,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype))
            #答问卷奖励调查币
            yesterday = formatting.date_add(-1).strftime("%Y%m%d") #昨天。根据WX_FANS.MULTIPLE取昨天所答问卷的发布用户累计数，为奖励倍数
            if not FSOBJ.get('MULTIPLE'):
                #统计该用户昨天所答问卷的发布用户累计数保存到WX_FANS.MULTIPLE
                rettmp = dbFrame.select("QN_ANSWERS A, QN_NAIRE N",what="N.FS_ID",vars=locals(),where="A.QN_ID=N.QN_ID AND DATE_FORMAT(A.INPUT_TIME,'%Y%m%d')=$yesterday AND A.FS_ID=$fsid",group="N.FS_ID").list()
                FSOBJ.MULTIPLE = '%s.%d'%(yesterday,len(rettmp))
                dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$fsid",MULTIPLE=FSOBJ.MULTIPLE)
            mltp = formatting.get_multiple(FSOBJ.get('MULTIPLE'),yesterday)
            coinjiangli = len(qitems)*mltp #奖励调查币：题目个数*1个*倍数
            dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,CHG_TYPE=15,CHG_AMOUNT=coinjiangli,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype),SUMMARY=QNOBJ.QN_ID)
            dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$fsid",COIN_TOTAL=web.SQLLiteral("COIN_TOTAL+%d"%(cointhanks+coinjiangli)),COIN_HOLD=web.SQLLiteral("COIN_HOLD+%d"%(cointhanks+coinjiangli)))
            FSOBJ.COIN_HOLD = FSOBJ.COIN_HOLD + (cointhanks+coinjiangli)
            FSOBJ.COIN_TOTAL = FSOBJ.COIN_TOTAL + (cointhanks+coinjiangli)
            cacher_fans_obj.set(fsid,FSOBJ) #更新缓存
            check_pause_naire3(FSOBJ)
            #保存答案，更新相关计数
            isnew = 1 if not FSOBJ.FIRSTANTIME else 0
            dbFrame.insert('QN_ANSWERS',AN_ID=anid,QN_ID=qnid,FS_ID=fsid,ANSWER_NO=anno,AN_CONTENT=content,AN_HONGBAO=hongbao1,ISNEW=isnew,CLIENTIP=clientip,AN_JIANGLI=coinjiangli)
            dbFrame.update('QN_NAIRE',vars=locals(),where="QN_ID=$qnid",NUM_LOTTERY=max(annos),NUM_VOTE=web.SQLLiteral("NUM_VOTE+1"),HONGBAO_SUM=(float(QNOBJ.HONGBAO_SUM) if QNOBJ.HONGBAO_SUM else 0)+hongbao1)
            if QNOBJ.QN_TYPE==2 and hongbao1>0:
                dbFrame.insert("QN_REDCACHE",CC_ID=utils.get_keyword(),OPENID=FSOBJ.OPENID,FS_ID=fsid,QN_ID=QNOBJ.QN_ID,AN_ID=anid,CC_HONGBAO=hongbao1,SUMMARY='答问卷抢红包')
                retval = add_fans_count(fsid, 'SUM_A2', hongbao1)
                if retval:
                    raise Exception(retval)
            #更新问卷统计结果
            options = dict([(x.QI_NO,{'QI_OPTION':formatting.json_object(x.QI_OPTION),'anstat':x.QI_ANSTAT}) for x in qitems])
            for qino,opidx in enumerate(json.loads(content),1): #如果做动态统计，在这个for外面再循环QN_ANSWERS即可
                anstat = json.loads(options[qino]['anstat']) if options[qino]['anstat'] else [0 for i in range(len(options[qino]['QI_OPTION']))]
                if opidx!=None and str(opidx).isdigit() and opidx>=0 and opidx<len(anstat):
                    anstat[opidx] += 1
                elif isinstance(opidx,list):
                    for i in opidx:
                        anstat[i] += 1
                else:
                    print 'ExceptionAnswer:',QNOBJ.QN_ID,content,qino,opidx
                options[qino]['anstat'] = json.dumps(anstat)
                dbFrame.update('QN_ITEMS',vars=locals(),where="QN_ID=$qnid and QI_NO=$qino",QI_ANSTAT=json.dumps(anstat))
            if not FSOBJ.FIRSTANTIME:
                #后面修改计数后会清fs缓存，这里不用清
                dbFrame.update('WX_FANS',vars=locals(),where="FS_ID=$fsid",FIRSTANTIME=utils.get_currdatetimestr(dbFrame.dbtype))
            #更新用户的计数字段
            retval = add_fans_count(fsid, 'COUNT_A%d'%QNOBJ.QN_TYPE)
            if retval:
                raise Exception(retval)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            print content
            print QNOBJ.QN_ID
            return {'error':e}
        else:
            t.commit()
    else:
        anno = ANOBJ.ANSWER_NO
    #答卷后的提示
    if QNOBJ.QN_TYPE==1:
        retmsg = u'你的抽奖号 %d，请关注公众号查询开奖情况。由于微信公众号发送客服消息限制，我们可能无法发送开奖和中奖通知，请您自助查询。'%anno
    elif QNOBJ.QN_TYPE==2:
        if hongbao1==0:
            retmsg = u'很遗憾没抢到红包！'
        else:
            retmsg = u'你抢得 %.2f 元红包'%hongbao1
            #如果是参与红包问卷，触发一下发红包
            retdat = check_wxpay_hong_and_send(fsid)
            if retdat.has_key('success'):
                hongbao1 = retdat['success']
                if hongbao1>=1:
                    retmsg += u'。累计需要发放 %.2f 元，请注意查收'%hongbao1
                else:
                    retmsg += u'。累计需要发放 %.2f 元，由于微信平台商户向粉丝发放红包金额限制，需要累计达到1元，届时会自动发放'%hongbao1
    elif QNOBJ.QN_TYPE==3:
        retmsg = u'感谢您参与！发卷人答谢%d调查币已发放到您的账号'%(round(QNOBJ.HONGBAO_MNY,0))
    else:
        retmsg = u''
    retmsg += u'<br>答卷获得%d调查币奖励'%coinjiangli
    retmsg += append_anshint(FSOBJ,QNOBJ)
    retval = {'success':retmsg}
    if QNOBJ.TOPIC_QNID and QNOBJ.QN_PUBLIC: #如果是一个话题问卷并且公开统计结果，直接跳转到问卷统计页面
        retval['seeurl'] = '/stview?fsid=%s&r=%s&qnid=%s'%(fsid,cacher_random_checker.genRandomValueForFSID(fsid),str(qnid))
    return retval

################################################################################
#问卷统计
def count_today_aire(fsid):
    '''统计今天指定用户发布的问卷个数。返回tuple(普通问卷个数,有奖问卷个数)'''
    today = utils.get_yyyymmdd()
    m = web.listget(dbFrame.select("QN_NAIRE",what="count(*) CNT",vars=locals(),where="QN_TYPE=0 and FS_ID=$fsid and INPUT_TIME=$today").list(),0,None)
    n = web.listget(dbFrame.select("QN_NAIRE",what="count(*) CNT",vars=locals(),where="QN_TYPE=1 and FS_ID=$fsid and INPUT_TIME=$today").list(),0,None)
    p = web.listget(dbFrame.select("QN_NAIRE",what="count(*) CNT",vars=locals(),where="QN_TYPE=2 and FS_ID=$fsid and INPUT_TIME=$today").list(),0,None)
    return (m.CNT if m else 0), (n.CNT if n else 0), (p.CNT if p else 0)

def count_aire(fsid):
    '''统计用户发布的问卷个数。返回tuple(普通问卷个数,有奖问卷个数,红包问卷个数)'''
    FSOBJ = get_fans_byfsid(fsid)
    return (FSOBJ.COUNT_P0 if FSOBJ and FSOBJ.COUNT_P0 else 0), (FSOBJ.COUNT_P1 if FSOBJ and FSOBJ.COUNT_P1 else 0), (FSOBJ.COUNT_P2 if FSOBJ and FSOBJ.COUNT_P2 else 0), (FSOBJ.COUNT_P3 if FSOBJ and FSOBJ.COUNT_P3 else 0)

def count_answer(fsid):
    '''统计用户答卷信息。返回tuple(普通问卷个数,有奖问卷个数,红包问卷个数)'''
    FSOBJ = get_fans_byfsid(fsid)
    return (FSOBJ.COUNT_A0 if FSOBJ and FSOBJ.COUNT_A0 else 0), (FSOBJ.COUNT_A1 if FSOBJ and FSOBJ.COUNT_A1 else 0), (FSOBJ.COUNT_A2 if FSOBJ and FSOBJ.COUNT_A2 else 0), (FSOBJ.COUNT_A3 if FSOBJ and FSOBJ.COUNT_A3 else 0)

def stat_qsnaire(qnid):
    '''动态统计问卷的答案'''
    m = dbFrame.select('QN_ITEMS',vars=locals(),where="QN_ID=$qnid").list()
    #静态统计：根据QN_ITEMS中记录的统计值
    options = dict([(x.QI_NO,{'QI_TITLE':x.QI_TITLE,'QI_OPTION':(['是','否','不确定'] if x.QI_TYPE=='B' else (['1星','2星','3星','4星','5星'] if x.QI_TYPE=='S' else formatting.json_object(x.QI_OPTION))),'QI_TYPE':x.QI_TYPE,'anstat':x.QI_ANSTAT}) for x in m])
    #动态统计：anstat初始值设为None
    # options = dict([(x.QI_NO,{'QI_TITLE':x.QI_TITLE,'QI_OPTION':(['是','否','不确定'] if x.QI_TYPE=='B' else (['1星','2星','3星','4星','5星'] if x.QI_TYPE=='S' else formatting.json_object(x.QI_OPTION))),'QI_TYPE':x.QI_TYPE,'anstat':None}) for x in m])
    m = dbFrame.select("QN_ANSWERS A, WX_FANS F",what="A.*,F.SEX,F.PROVINCE,F.CITY,F.P2_AGE,F.P2_MARRIAGE,F.P2_ACADEMIC,F.P2_INCOME",vars=locals(),where="A.FS_ID=F.FS_ID AND A.QN_ID=$qnid").list()
    basestat = {
        1: {'QI_TITLE':'性别','QI_OPTION':['未知','男','女'],'QI_TYPE':'R','anstat':None},
        2: {'QI_TITLE':'年龄','QI_OPTION':['未知','20岁及以下','21-25岁','26-30岁','31-40岁','41-50岁','51-60岁','60岁以上'],'QI_TYPE':'R','anstat':None},
        3: {'QI_TITLE':'婚姻状况','QI_OPTION':['未知','已婚','未婚'],'QI_TYPE':'R','anstat':None},
        4: {'QI_TITLE':'最高学历','QI_OPTION':['未知','初中及以下','高中/中专','大专','本科','硕士','博士'],'QI_TYPE':'R','anstat':None},
        5: {'QI_TITLE':'月收入','QI_OPTION':['未知','1000元以下','1001-2000元','2001-3000元','3001-5000元','5001-8000元','8001-10000元','10001-20000元','20000元以上'],'QI_TYPE':'R','anstat':None},
        6: {'QI_TITLE':'省份','QI_OPTION':[u'未知'],'QI_TYPE':'R','anstat':None},
        7: {'QI_TITLE':'城市','QI_OPTION':[u'未知'],'QI_TYPE':'R','anstat':None},
    }
    for ans in m: #先循环一次把省份和城市的选项清单生成出来
        basestat[6]['QI_OPTION'].append(u'未知' if not ans.PROVINCE else ans.PROVINCE)
        basestat[6]['QI_OPTION'] = list(set(basestat[6]['QI_OPTION']))
        basestat[7]['QI_OPTION'].append(u'未知' if not ans.CITY else ans.CITY)
        basestat[7]['QI_OPTION'] = list(set(basestat[7]['QI_OPTION']))
    #循环处理题目的回答
    for ans in m:
        #如果做动态统计，循环QN_ANSWERS时再处理每个答案进行统计
        # for qino,opidx in enumerate(json.loads(ans.AN_CONTENT),1):
        #     anstat = json.loads(options[qino]['anstat']) if options[qino]['anstat'] else [0 for i in range(len(options[qino]['QI_OPTION']))]
        #     if opidx!=None and str(opidx).isdigit() and opidx>=0 and opidx<len(anstat):
        #         anstat[opidx] += 1
        #     elif isinstance(opidx,list):
        #         for i in opidx:
        #             anstat[i] += 1
        #     else:
        #         print 'ExceptionAnswer:',qnid,ans.AN_CONTENT,qino,opidx
        #     options[qino]['anstat'] = json.dumps(anstat)
        #用户基本信息
        #1性别
        qino = 1
        opidx = 0 if ans.SEX==None else ans.SEX
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #2年龄
        qino = 2
        opidx = 0 if ans.P2_AGE==None else utils.unpow2(ans.P2_AGE)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #3婚姻
        qino = 3
        opidx = 0 if ans.P2_MARRIAGE==None else utils.unpow2(ans.P2_MARRIAGE)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #4学历
        qino = 4
        opidx = 0 if ans.P2_ACADEMIC==None else utils.unpow2(ans.P2_ACADEMIC)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #5收入
        qino = 5
        opidx = 0 if ans.P2_INCOME==None else utils.unpow2(ans.P2_INCOME)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #6省份
        qino = 6
        opidx = basestat[qino]['QI_OPTION'].index(u'未知' if not ans.PROVINCE else ans.PROVINCE)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
        #7城市
        qino = 7
        opidx = basestat[qino]['QI_OPTION'].index(u'未知' if not ans.CITY else ans.CITY)
        anstat = json.loads(basestat[qino]['anstat']) if basestat[qino]['anstat'] else [0 for i in range(len(basestat[qino]['QI_OPTION']))]
        anstat[opidx] += 1
        basestat[qino]['anstat'] = json.dumps(anstat)
    retval1 = [{"QI_TITLE":x["QI_TITLE"], "QI_TYPE":x["QI_TYPE"], "pldata":[{"label":x['QI_OPTION'][i],"data":(json.loads(x['anstat'])[i] if x['anstat'] else [])} for i in range(len(x['QI_OPTION']))]} for x in options.values()]
    retval2 = [{"QI_TITLE":x["QI_TITLE"], "QI_TYPE":x["QI_TYPE"], "pldata":[{"label":x['QI_OPTION'][i],"data":(json.loads(x['anstat'])[i] if x['anstat'] else [])} for i in range(len(x['QI_OPTION']))]} for x in basestat.values()]
    return retval1,retval2

def get_value(value):
    '''为导出excel时处理值用。主要是日期时间、数值需要转换'''
    from datetime import datetime, date, timedelta
    from decimal import Decimal
    if isinstance(value, str):
        value = unicode(value)
    elif isinstance(value, datetime):
        value = value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, timedelta): # 对应mysql的time字段类型
        value = str(value) # [H]H:MM:SS
        if len(value) == 7:
            value = '0'+value
    elif isinstance(value, Decimal):
        # from config import formatting
        # value = formatting.format_Decimal(value)
        value = unicode(str(value))
    # return formatting.format_date(value, '%Y-%m-%d')
    if value==None:
        value = u''
    return value
def export_answer_excel(qnid):
    '''将问卷答卷导出到excel文件'''
    import xlwt
    from cStringIO import StringIO
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
    #所有题目一个Sheet，所有回答一个Sheet
    #每份回答一行，每个题目一列（列标题使用Q+题目序号）
    workbook = xlwt.Workbook()
    #题目页
    option = dbFrame.select("QN_ITEMS",vars=locals(),where="QN_ID=$qnid",order="QI_NO").list()
    ws0 = workbook.add_sheet(u'题目')
    ws0.write(0,0,u'序号', styleNormal)
    ws0.write(0,1,u'题目', styleNormal)
    for row,opt in enumerate(option,1):
        ws0.write(row,0,row, styleNormal)
        ws0.write(row,1,opt['QI_TITLE'], styleNormal)
    #答卷页
    list_option = [json.loads(x.QI_OPTION) for x in option]
    ws1 = workbook.add_sheet(u'答卷')
    answer = dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid",order="ANSWER_NO").list()
    ws1.write(0,0,u'序号', styleNormal)
    ws1.write(0,1,u'答卷时间', styleNormal)
    ws1.write(0,2,u'用户IP', styleNormal)
    for idx,opt in enumerate(option,1):
        ws1.write(0,2+idx,u'Q%d'%idx, styleNormal)
    for row,ans in enumerate(answer,1):
        ws1.write(row,0,row, styleNormal)
        ws1.write(row,1,get_value(ans['INPUT_TIME']), styleNormal)
        ws1.write(row,2,ans['CLIENTIP'], styleNormal)
        ancontent = json.loads(ans['AN_CONTENT'])
        for col,val in enumerate(ancontent,3):
            if isinstance(val,list):
                optitle = u'，'.join([list_option[col-3][x] if x<len(list_option[col-3]) else '' for x in val])
            elif col and val:
                optitle = list_option[col-3][val] if val<len(list_option[col-3]) else ''
            else:
                optitle = ''
            ws1.write(row,col,optitle, styleNormal)
    #保存
    fakefile = StringIO()
    workbook.save(fakefile)
    retval = fakefile.getvalue()
    fakefile.close()
    return retval

################################################################################
#中奖与兑奖相关
def count_award(fsid):
    '''返回用户中奖次数，红包总金额'''
    FSOBJ = get_fans_byfsid(fsid)
    return (FSOBJ.COUNT_WIN if FSOBJ and FSOBJ.COUNT_WIN else 0), (float(FSOBJ.SUM_A2) if FSOBJ and FSOBJ.SUM_A2 else 0)

def catch_hq(yyyymmdd):
    '''从深交所网站获取指定日期的深成指成交金额并保存在数据库中'''
    m = web.listget(dbFrame.select("SJSHQ",vars=locals(),where="HQRQ=$yyyymmdd AND HQZQDM='399001'").list(),0,None)
    if m and m.HQCJJE:
        return {'success':m.HQCJJE}
    else:
        cjje = utils.get_399001(yyyymmdd)
        if cjje and formatting.isfloat(cjje):
            cjje = long(float(cjje)*100)
            t = dbFrame.transaction()
            try:
                dbFrame.insert("SJSHQ",HQ_ID=utils.get_keyword(),HQRQ=yyyymmdd,HQZQDM='399001',HQCJJE=cjje)
            except Exception, e:
                t.rollback()
                traceback.print_exc()
                return {'error':e}
            else:
                t.commit()
                return {'success':cjje}
        else:
            return {'error':'无数据'+str(cjje)}
def list_needdraw():
    '''取已结束需要抽奖的有奖问卷'''
    retval = [append_naire_imgurl(x) for x in dbFrame.select("QN_NAIRE",vars=locals(),where="QN_TYPE=1 AND QN_STATUS=9 AND END_DATE IS NULL").list()]
    return retval
def get_winfs(qnid,winno):
    '''获取中奖用户的FSID和OPENID'''
    m = web.listget(dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid AND ANSWER_NO=$winno").list(),0,None)
    fsid = m.FS_ID if m else ''
    if not fsid: #答卷表中没有中奖号，再到抽奖号分配表中查询
        m = web.listget(dbFrame.select("QN_LOTTERY",vars=locals(),where="QN_ID=$qnid AND LOTTERY_NO=$winno").list(),0,None)
        fsid = m.FS_ID if m else ''
    return get_fans_byfsid(fsid)
def set_award(qnid,winno,hq399001):
    '''保存有奖问卷的中奖信息。返回中奖用户对象'''
    FSWIN = get_winfs(qnid,winno)
    if not FSWIN.FS_ID:
        return {'error':'获取中奖用户出现问题，问卷ID：%s，中奖号：%d'%(qnid,winno)}
    serial = utils.get_keyword()
    t = dbFrame.transaction()
    try:
        dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid",WIN_NO=winno,NUM_399001=hq399001,WIN_SERIAL=serial,WIN_FSID=FSWIN.FS_ID)
        add_fans_count(FSWIN.FS_ID,'COUNT_WIN')
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':FSWIN}

def list_needback():
    '''取已结束的需要退红包款的红包问卷'''
    #不集中退红包，该函数未用到
    return dbFrame.select("QN_NAIRE",vars=locals(),where="QN_TYPE=2 AND QN_STATUS=9 AND PRIZE_VALUE-FARE>HONGBAO_SUM AND WIN_END=0").list()
def set_qsend(qnid,enddate,winend=None,expno=''):
    '''设置问卷为已兑奖/已退款状态，结束日期(行情日期)'''
    savedata = {}
    if enddate:
        savedata['END_DATE'] = enddate
    if winend:
        savedata['WIN_END'] = winend
    if expno:
        savedata['AN_EXPNO'] = expno
    if savedata:
        t = dbFrame.transaction()
        try:
            dbFrame.update("QN_NAIRE",vars=locals(),where="QN_ID=$qnid",**savedata)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':e}
        else:
            t.commit()
            return {'success':qnid}
    else:
        return {'error':'结束日期和兑奖状态不能都为空'}
def set_address(qnid,anid,adr,phn):
    '''设置中奖信息：通信地址/电话'''
    ma = web.listget(dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid AND AN_ID=$anid").list(),0,None)
    t = dbFrame.transaction()
    try:
        if ma:
            dbFrame.update("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid AND AN_ID=$anid",AN_ADDRESS=adr,AN_PHONE=phn)
        else:
            dbFrame.update("QN_LOTTERY",vars=locals(),where="QN_ID=$qnid AND LT_ID=$anid",LT_ADDRESS=adr,LT_PHONE=phn)
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return {'error':e}
    else:
        t.commit()
        return {'success':qnid}


################################################################################
#问卷模板相关
def list_template():
    '''返回模板问卷及其题目'''
    retval = dbFrame.select("QN_NAIRE",what="QN_ID,QN_TITLE",where="QN_STATUS>=10 and QN_STATUS<=89").list()
    for x in retval:
        items = dbFrame.select("QN_ITEMS",what="QI_ID,QI_TYPE,QI_OPTION,QI_TITLE",vars=locals(),where="QN_ID=$x.QN_ID",order="QI_NO").list()
        for y in items:
            y['QI_OPTION'] = json.loads(y['QI_OPTION'])
        x['ITEMS'] = items
    return retval
def list_mytmpl(fsid):
    '''取指定用户发布的问卷作为模板。只取QN_NAIRE的，不含归档的'''
    retval = dbFrame.select("QN_NAIRE",what="QN_ID,QN_TITLE",vars=locals(),where="FS_ID=$fsid and QN_STATUS in (2,3,9)",order="INPUT_TIME").list()
    for x in retval:
        items = dbFrame.select("QN_ITEMS",what="QI_ID,QI_TYPE,QI_OPTION,QI_TITLE",vars=locals(),where="QN_ID=$x.QN_ID",order="QI_NO").list()
        for y in items:
            y['QI_OPTION'] = json.loads(y['QI_OPTION'])
        x['ITEMS'] = items
    return retval

################################################################################
#归档管理
def archive_qsnaire(yyyymmdd):
    '''将指定日期前的已结束已兑奖问卷移到主归档表'''
    ts = int(time.mktime( time.strptime(yyyymmdd, "%Y%m%d") ))
    m = web.listget(dbFrame.query("SELECT COUNT(*) CNT FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s"%yyyymmdd),0,None)
    if m and m.CNT:
        t = dbFrame.transaction()
        try:
            #选删除目标表中将要复制过来的记录避免重复
            dbFrame.query("DELETE FROM QNHIS_REDSERIAL_MAIN WHERE RS_ID IN (SELECT RS_ID FROM QN_REDSERIAL WHERE INPUT_TIME<%s)"%(yyyymmdd+'000000'))
            dbFrame.query("DELETE FROM QNHIS_ITEMS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QNHIS_LOTTERY_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QNHIS_ANSWERS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QNHIS_NAIRE_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM WXHIS_COINDETAIL_MAIN WHERE CD_ID IN (SELECT CD_ID FROM WX_COINDETAIL WHERE DATE_FORMAT(INSERTTIME,'%Y%m%d')<"+yyyymmdd+")")
            dbFrame.query("DELETE FROM WXHIS_LOGS_MAIN WHERE CREATETIME<%d"%ts)
            #复制数据
            dbFrame.query("INSERT INTO QNHIS_REDSERIAL_MAIN SELECT * FROM QN_REDSERIAL WHERE INPUT_TIME<%s"%(yyyymmdd+'000000'))
            dbFrame.query("INSERT INTO QNHIS_ITEMS_MAIN SELECT * FROM QN_ITEMS WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("INSERT INTO QNHIS_LOTTERY_MAIN SELECT * FROM QN_LOTTERY WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("INSERT INTO QNHIS_ANSWERS_MAIN SELECT * FROM QN_ANSWERS WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("INSERT INTO QNHIS_NAIRE_MAIN SELECT * FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s"%yyyymmdd)
            dbFrame.query("INSERT INTO WXHIS_COINDETAIL_MAIN SELECT * FROM WX_COINDETAIL WHERE DATE_FORMAT(INSERTTIME,'%Y%m%d')<"+yyyymmdd)
            dbFrame.query("INSERT INTO WXHIS_LOGS_MAIN SELECT * FROM WX_LOGS WHERE CREATETIME<%d"%ts)
            #删除源表数据
            dbFrame.query("DELETE FROM QN_REDSERIAL WHERE INPUT_TIME<%s"%(yyyymmdd+'000000'))
            dbFrame.query("DELETE FROM QN_ITEMS WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QN_LOTTERY WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QN_ANSWERS WHERE QN_ID IN (SELECT QN_ID FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s)"%yyyymmdd)
            dbFrame.query("DELETE FROM QN_NAIRE WHERE QN_STATUS in (8,9) AND WIN_END=2 AND INPUT_TIME<%s"%yyyymmdd)
            dbFrame.query("DELETE FROM WX_COINDETAIL WHERE DATE_FORMAT(INSERTTIME,'%Y%m%d')<"+yyyymmdd)
            dbFrame.query("DELETE FROM WX_LOGS WHERE CREATETIME<%d"%ts)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':str(e)}
        else:
            t.commit()
            return {'success':str(m.CNT)}
    else:
        return {'success':'0'}
def archive_year(yyyy):
    '''将主归档表中的指定年份的数据移到年度归档表'''
    from datetime import datetime
    curryear = str(datetime.now().year)
    if yyyy>=curryear:
        return {'error':'本年的数据保留在主归档表'}
    #如果年度归档表不存在就先创建
    if not table_exists(dbFrame,"QNHIS_NAIRE_"+yyyy):
        t = dbFrame.transaction()
        try:
            dbFrame.query("CREATE TABLE "+"QNHIS_REDSERIAL_"+yyyy+" LIKE QN_REDSERIAL")
            dbFrame.query("CREATE TABLE "+"QNHIS_NAIRE_"+yyyy+" LIKE QN_NAIRE")
            dbFrame.query("CREATE TABLE "+"QNHIS_ITEMS_"+yyyy+" LIKE QN_ITEMS")
            dbFrame.query("CREATE TABLE "+"QNHIS_ANSWERS_"+yyyy+" LIKE QN_ANSWERS")
            dbFrame.query("CREATE TABLE "+"QNHIS_LOTTERY_"+yyyy+" LIKE QN_LOTTERY")
            dbFrame.query("CREATE TABLE "+"WXHIS_COINDETAIL_"+yyyy+" LIKE WX_COINDETAIL")
            dbFrame.query("CREATE TABLE "+"WXHIS_LOGS_"+yyyy+" LIKE WX_LOGS")
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':str(e)}
        else:
            t.commit()
    m = web.listget(dbFrame.query("SELECT COUNT(*) CNT FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s"%yyyy),0,None)
    if m and m.CNT:
        #复制数据
        t = dbFrame.transaction()
        try:
            #选删除目标表中将要复制过来的记录避免重复
            dbFrame.query("DELETE FROM QNHIS_REDSERIAL_"+yyyy+" WHERE RS_ID IN (SELECT RS_ID FROM QNHIS_REDSERIAL_MAIN WHERE INPUT_TIME<%s)"%(yyyy+'1232000000'))
            dbFrame.query("DELETE FROM QNHIS_ITEMS_"+yyyy+" WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_LOTTERY_"+yyyy+" WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_ANSWERS_"+yyyy+" WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_NAIRE_"+yyyy+" WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM WXHIS_COINDETAIL_"+yyyy+" WHERE CD_ID IN (SELECT CD_ID FROM WXHIS_COINDETAIL_MAIN WHERE DATE_FORMAT(INSERTTIME,'%Y')="+yyyy+")")
            #复制数据
            dbFrame.query("INSERT INTO QNHIS_REDSERIAL_"+yyyy+" SELECT * FROM QNHIS_REDSERIAL_MAIN WHERE INPUT_TIME<%s"%(yyyy+'1232000000'))
            dbFrame.query("INSERT INTO QNHIS_ITEMS_"+yyyy+" SELECT * FROM QNHIS_ITEMS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("INSERT INTO QNHIS_LOTTERY_"+yyyy+" SELECT * FROM QNHIS_LOTTERY_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("INSERT INTO QNHIS_ANSWERS_"+yyyy+" SELECT * FROM QNHIS_ANSWERS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("INSERT INTO QNHIS_NAIRE_"+yyyy+" SELECT * FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s"%yyyy)
            dbFrame.query("INSERT INTO WXHIS_COINDETAIL_"+yyyy+" SELECT * FROM WXHIS_COINDETAIL_MAIN WHERE DATE_FORMAT(INSERTTIME,'%Y')="+yyyy)
            #删除源表数据
            dbFrame.query("DELETE FROM QNHIS_REDSERIAL_MAIN WHERE INPUT_TIME<%s"%(yyyy+'1232000000'))
            dbFrame.query("DELETE FROM QNHIS_ITEMS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_LOTTERY_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_ANSWERS_MAIN WHERE QN_ID IN (SELECT QN_ID FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s)"%yyyy)
            dbFrame.query("DELETE FROM QNHIS_NAIRE_MAIN WHERE INPUT_TIME div 10000=%s"%yyyy)
            dbFrame.query("DELETE FROM WXHIS_COINDETAIL_MAIN WHERE DATE_FORMAT(INSERTTIME,'%Y')="+yyyy)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return {'error':str(e)}
        else:
            t.commit()
            return {'success':str(m.CNT)}
    else:
        return {'success':'0'}

def list_his_partin(fsid,yyyy):
    '''取参与过的问卷(归档)'''
    #取归档问卷原则：取当前年份的话从主归档表中查，取历史年份的话从对应年份归档表中查
    from datetime import datetime
    curryear = str(datetime.now().year)
    tbname = 'MAIN' if yyyy==curryear else yyyy
    if table_exists(dbFrame,"QNHIS_NAIRE_"+tbname):
        retval = dbFrame.select("QNHIS_NAIRE_"+tbname+" N, QNHIS_ANSWERS_"+tbname+" A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.AN_ID,A.ANSWER_NO,A.AN_CONTENT,A.AN_HONGBAO,A.AN_ADDRESS,A.AN_PHONE",
            vars=locals(),where="N.QN_ID=A.QN_ID AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list()
        if retval==[]: #如果本次所查归档表中无数据，再查上一年份归档表
            retval = list_his_partin(fsid,str(int(yyyy)-1))
    else:
        retval = None
    return retval
def list_his_myaire(fsid,yyyy):
    '''取指定用户发布的问卷(归档)'''
    from datetime import datetime
    curryear = str(datetime.now().year)
    tbname = 'MAIN' if yyyy==curryear else yyyy
    if table_exists(dbFrame,"QNHIS_NAIRE_"+tbname):
        retval = dbFrame.select("QNHIS_NAIRE_"+tbname,vars=locals(),where="FS_ID=$fsid and QN_STATUS<10",order="INPUT_TIME DESC,QN_STATUS").list()
        for x in retval:
            x.QN_STATUS_NAME = formatting.get_status_title(x.QN_STATUS)
        if retval==[]: #如果本次所查归档表中无数据，再查上一年份归档表
            retval = list_his_myaire(fsid,str(int(yyyy)-1))
    else:
        retval = None
    return retval
def list_his_award(fsid,yyyy):
    '''取指定用户的中奖和获取红包记录(归档)'''
    from datetime import datetime
    curryear = str(datetime.now().year)
    tbname = 'MAIN' if yyyy==curryear else yyyy
    if table_exists(dbFrame,"QNHIS_NAIRE_"+tbname):
        retval = dbFrame.select("QNHIS_NAIRE_"+tbname+" N, QNHIS_ANSWERS_"+tbname+" A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.AN_ID,A.ANSWER_NO,A.AN_CONTENT,A.AN_HONGBAO,A.AN_ADDRESS,A.AN_PHONE",
            vars=locals(),where="N.QN_ID=A.QN_ID AND (N.WIN_NO=A.ANSWER_NO OR AN_HONGBAO>0) AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list()
        retval.extend(dbFrame.select("QNHIS_NAIRE_"+tbname+" N, QNHIS_LOTTERY_"+tbname+" A",what="N.*,A.FS_ID AN_FS_ID,A.INPUT_TIME AN_INPUT_TIME,A.LT_ID AN_ID,A.LOTTERY_NO ANSWER_NO,'' AN_CONTENT,0 AN_HONGBAO,A.LT_ADDRESS AN_ADDRESS,A.LT_PHONE AN_PHONE",
            vars=locals(),where="N.QN_ID=A.QN_ID AND (N.WIN_NO=A.LOTTERY_NO) AND A.FS_ID=$fsid",order="A.INPUT_TIME DESC").list())
        retval.sort(key=lambda x: x['AN_INPUT_TIME'], reverse=True)
        if retval==[]: #如果本次所查归档表中无数据，再查上一年份归档表
            retval = list_his_award(fsid,str(int(yyyy)-1))
    else:
        retval = None
    return retval


################################################################################
def req_qr():
    '''获取永久二维码'''
    m = dbFrame.select("WX_QRCODE",where="IS_SALER=1 AND (QR_TICKET IS NULL OR QR_TICKET='')").list()
    if m:
        import mforweixin
        t = dbFrame.transaction()
        try:
            for x in m:
                print x.SCENE_ID,
                qret = mforweixin.get_qrwithparam(x.SCENE_ID,True)
                if qret.has_key('sceneid') and qret.has_key('ticket'):
                    print qret.has_key('ticket')
                    dbFrame.update("WX_QRCODE",vars=locals(),where="SCENE_ID=$x.SCENE_ID",QR_TICKET=qret['ticket'])
                else:
                    print qret
                time.sleep(1)
        except Exception, e:
            t.rollback()
            traceback.print_exc()
        else:
            t.commit()

def list_topics():
    '''根据sys:topic_qnid的配置获取问卷'''
    retval = dbFrame.query("SELECT * FROM QN_NAIRE WHERE QN_ID IN (SELECT CFG_VAL FROM QN_CONFIGURATION WHERE CFG_KEY LIKE 'sys:topic_qnid%') ORDER BY INPUT_TIME DESC").list()
    retval = [append_naire_imgurl(x) for x in retval]
    return retval

def get_fsid_by_sceneid(sceneid):
    '''根据SCENE_ID取营销人员'''
    m = web.listget(dbFrame.select("WX_QRCODE",vars=locals(),where="SCENE_ID=$sceneid").list(),0,None)
    return m.BUSI_ID if m else sceneid
def set_saler(fsid):
    '''设置营销人员'''
    SLOBJ = web.listget(dbFrame.select("WX_QRCODE",vars=locals(),where="BUSI_ID=$fsid").list(),0,None)
    if not SLOBJ:
        maxid = web.listget(dbFrame.select("WX_QRCODE",what="max(SCENE_ID) SCENE_ID").list(),0,{}).get('SCENE_ID',20000)
        maxid = (maxid if maxid else 0) + 1
        import mforweixin
        t = dbFrame.transaction()
        try:
            qret = mforweixin.get_qrwithparam(maxid,True)
            qrticket = ''
            if qret.has_key('sceneid') and qret.has_key('ticket'):
                qrticket = qret['ticket']
            dbFrame.insert("WX_QRCODE",SCENE_ID=maxid,BUSI_ID=fsid,IS_SALER=1,QR_TICKET=qrticket,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype))
        except Exception, e:
            t.rollback()
            traceback.print_exc()
            return e
        else:
            t.commit()
            web.config.app_configuration['run:saler'].append(fsid)
    return ''
def update_today_apply():
    '''设置当天申请推广计划的用户清单'''
    t = dbFrame.transaction()
    try:
        web.config.app_configuration['run:today_apply'] = json.dumps(web.config.today_apply)
        dbFrame.update("QN_CONFIGURATION",where="CFG_KEY='run:today_apply'",CFG_VAL=web.config.app_configuration['run:today_apply'])
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return e
    else:
        t.commit()

################################################################################
def list_uncomplete_naire(yyyymmdd):
    '''取指定日期未完成的问卷'''
    return dbFrame.select("QN_NAIRE N, WX_FANS F",what="F.FS_ID,F.OPENID,N.QN_TITLE,N.QN_TYPE,N.QN_STATUS",vars=locals(),
        where="N.FS_ID=F.FS_ID AND N.INPUT_TIME=$yyyymmdd AND N.QN_STATUS<2").list()

def list_nosale_saler():
    '''返回刚加入推广计划后第一天没有推广数据的用户'''
    maxdate = web.listget(dbFrame.select("WX_MARKETDETAIL",what="max(YYYYMMDD) YYYYMMDD").list(),0,{}).get('YYYYMMDD')
    if not maxdate:
        maxdate = formatting.date_add(-1,datetime.datetime.today()).strftime("%Y%m%d") #1天前
    retval = dbFrame.select("WX_QRCODE S, WX_MARKETDETAIL M, WX_FANS F",what="F.FS_ID,F.OPENID,S.INSERTTIME",vars=locals(),
        where="F.FS_ID=S.BUSI_ID AND S.BUSI_ID=M.FS_ID AND S.IS_SALER=1 AND (S.IS_ADMIN!=1 OR S.IS_ADMIN IS NULL) AND DATE_FORMAT(S.INSERTTIME,'%Y%m%d')=M.DATE_D1 AND M.YYYYMMDD=$maxdate").list()
    return retval

def get_ad_byqn(qnid):
    '''根据qnid获取广告'''
    m = web.listget(dbFrame.select("QN_ADVERTISE",vars=locals(),where="QN_ID=$qnid").list(),0,None)
    return m.CONTENT if m and m.CONTENT else ''

################################################################################
def set_sign(fsid,yyyymmdd):
    '''用户签到。返回(本次签到获得调查币,调查币余额,连续签到天数)，出错返回(-1,调查币余额,-1)，已签到返回(0,调查币余额,连续签到天数)'''
    if not yyyymmdd:
        yyyymmdd = datetime.datetime.today().strftime("%Y%m%d")
    currday = datetime.datetime.strptime(yyyymmdd, "%Y%m%d")
    yesterday = formatting.date_add(-1,currday).strftime("%Y%m%d") #昨天
    FSOBJ = get_fans_byfsid(fsid)
    #如果昨天签过到，取累计签到天数加1。否则为连续1天
    if FSOBJ.get('SIGN_MARK') and FSOBJ.SIGN_MARK.startswith(yyyymmdd):
        days = FSOBJ.SIGN_MARK.split('.')[1]
        days = int(days) if days.isdigit() else 1
        return 0,FSOBJ.COIN_HOLD,days
    elif FSOBJ.get('SIGN_MARK') and FSOBJ.SIGN_MARK.startswith(yesterday):
        days = FSOBJ.SIGN_MARK.split('.')[1]
        days = int(days)+1 if days.isdigit() else 1
    else:
        days = 1
    t = dbFrame.transaction()
    try:
        mark = "%s.%d"%(yyyymmdd,days)
        dbFrame.update("WX_FANS",vars=locals(),where="FS_ID=$fsid",SIGN_MARK=mark,COIN_TOTAL=web.SQLLiteral('COIN_TOTAL+%d*10'%days),COIN_HOLD=web.SQLLiteral('COIN_HOLD+%d*10'%days))
        dbFrame.insert("WX_COINDETAIL",CD_ID=utils.get_keyword(),FS_ID=fsid,INSERTTIME=utils.get_currdatetimestr(dbFrame.dbtype),CHG_AMOUNT=days*10,CHG_TYPE=13)
        FSOBJ['SIGN_MARK'] = mark
        FSOBJ['COIN_TOTAL'] = FSOBJ.get('COIN_TOTAL',0)+days*10
        FSOBJ['COIN_HOLD'] = FSOBJ.get('COIN_HOLD',0)+days*10
        cacher_fans_obj.set(fsid,FSOBJ) #更新缓存
    except Exception, e:
        t.rollback()
        traceback.print_exc()
        return -1,FSOBJ.COIN_HOLD,-1
    else:
        t.commit()
    return days*10,FSOBJ.COIN_HOLD,days

################################################################################
def test():
    print get_fans_byfsid(10000)
    print get_fans_byopenid('olJ2zuADCnfNFhGimO_6ggECTvTs')
