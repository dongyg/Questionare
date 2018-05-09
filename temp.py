#!/usr/bin/env python
# -*- coding: utf-8 -*-

from config import *
InitSystem()
from config import *

def f1216():
    retval = {}
    p = dbFrame.query("select * from t1216 where id like '__0000' order by id").list()
    for x in p:
        c = dbFrame.query("select * from t1216 where id like '%s____' and id<>'%s'"%(x.id[:2],x.id)).list()
        retval[x.title] = [y.title for y in c]
    return retval
def f20180303():
    # 发现从20171215起，mdb.get_hongbao_cache的字符串连接会出错，红包都没发出去。从 QN_REDCACHE 从汇总整理一下，手工进行补发
    # select FS_ID, SUM(CC_HONGBAO) from QN_REDCACHE group by FS_ID having SUM(CC_HONGBAO)>=1;

    # 1402935851  5.09
    # 1431569348  1.00
    # 1523296906  1.00
    # 1597031554  1.00
    # 1668332639  1.00
    # 1946659292  1.50
    # 2088628454  1.00
    # 2399401554  1.00
    # 2556358340  1.00
    # 3153340522  1.00
    # 3220087225  5.83
    # 3337264593  3.98
    # 3625914839  9.94
    # 3710625361  101.88
    # 3790643966  9.94
    # 3868938086  198.80
    # 3953371524  1988.99

    # print mdb.check_wxpay_hong_and_send(1402935851)
    # print mdb.check_wxpay_hong_and_send(1431569348)
    # print mdb.check_wxpay_hong_and_send(1523296906)
    # print mdb.check_wxpay_hong_and_send(1597031554)
    # print mdb.check_wxpay_hong_and_send(1668332639)
    # print mdb.check_wxpay_hong_and_send(1946659292)
    # print mdb.check_wxpay_hong_and_send(2088628454)
    # print mdb.check_wxpay_hong_and_send(2399401554)
    # print mdb.check_wxpay_hong_and_send(2556358340)
    # print mdb.check_wxpay_hong_and_send(3153340522)
    # print mdb.check_wxpay_hong_and_send(3220087225)
    # print mdb.check_wxpay_hong_and_send(3337264593)
    # print mdb.check_wxpay_hong_and_send(3625914839)
    # print mdb.check_wxpay_hong_and_send(3710625361)
    # print mdb.check_wxpay_hong_and_send(3790643966)
    # print mdb.check_wxpay_hong_and_send(3868938086)
    # print mdb.check_wxpay_hong_and_send(3953371524)
    time.sleep(5)

def f20180420():
    # 发现从20180311起，check_wxpay_hong_and_send中执行madin.sendToMe(hongbaodetail)时，没有导入madmin，因为放在了插入QN_REDSERIAL数据和sendredpack前面，
    # 所以，红包都没发出去，QN_REDSERIAL未生成发送数据。现从 QN_REDCACHE 从汇总整理一下，手工进行补发
    # select FS_ID, SUM(CC_HONGBAO) from QN_REDCACHE group by FS_ID having SUM(CC_HONGBAO)>=1;
    # 1597555573, 1.23
    # 3563243246, 3.58
    # 4076390107, 4.97
    # 4090803051, 2.42
    # 4091949854, 2.55
    # 4092079150, 4.56
    # 4093639434, 4.81
    # 4094473412, 3.86
    # 4161894395, 194.39
    # 4237695383, 27.65

    # print mdb.check_wxpay_hong_and_send(1597555573)
    # print mdb.check_wxpay_hong_and_send(3563243246)
    # print mdb.check_wxpay_hong_and_send(4076390107)
    # print mdb.check_wxpay_hong_and_send(4090803051)
    # print mdb.check_wxpay_hong_and_send(4091949854)
    # print mdb.check_wxpay_hong_and_send(4092079150)
    # print mdb.check_wxpay_hong_and_send(4093639434)
    # print mdb.check_wxpay_hong_and_send(4094473412)
    # print mdb.check_wxpay_hong_and_send(4161894395)
    # print mdb.check_wxpay_hong_and_send(4237695383)
    time.sleep(5)

def f20180506():
    # 问卷 fc2f390f50eb11e884c7a2bee322aa3b 的每个红包是 1.1，都没发出去，因为 mdb.check_wxpay_hong_and_send 中的 madmin.sendToMe('%d: %.2f'%(fsid,amount)) fsid是unicode出错了
    print db.check_wxpay_hong_and_send(4556804721)
    # print db.check_wxpay_hong_and_send(4559091828)
    # print db.check_wxpay_hong_and_send(4559094316)
    # print db.check_wxpay_hong_and_send(4559095392)
    # print db.check_wxpay_hong_and_send(4559098961)
    # print db.check_wxpay_hong_and_send(4559101884)
    # print db.check_wxpay_hong_and_send(4559102900)
    # print db.check_wxpay_hong_and_send(4559109156)
    # print db.check_wxpay_hong_and_send(4559114327)
    # print db.check_wxpay_hong_and_send(4559117613)
    # print db.check_wxpay_hong_and_send(4559123062)
    # print db.check_wxpay_hong_and_send(4559125112)
    # print db.check_wxpay_hong_and_send(4559127317)
    # print db.check_wxpay_hong_and_send(4559129421)
    # print db.check_wxpay_hong_and_send(4559133052)
    # print db.check_wxpay_hong_and_send(4559140961)
    # print db.check_wxpay_hong_and_send(4559148055)
    # print db.check_wxpay_hong_and_send(4559148483)
    # print db.check_wxpay_hong_and_send(4559175352)
    # print db.check_wxpay_hong_and_send(4559185484)
    # print db.check_wxpay_hong_and_send(4559227837)
    # print db.check_wxpay_hong_and_send(4559238616)
    # print db.check_wxpay_hong_and_send(4559242680)
    # print db.check_wxpay_hong_and_send(4559264300)
    # print db.check_wxpay_hong_and_send(4559268952)
    # print db.check_wxpay_hong_and_send(4559280139)
    # print db.check_wxpay_hong_and_send(4559291103)
    # print db.check_wxpay_hong_and_send(4559327397)
    # print db.check_wxpay_hong_and_send(4559330560)
    # print db.check_wxpay_hong_and_send(4559374282)
    # print db.check_wxpay_hong_and_send(4559410926)
    # print db.check_wxpay_hong_and_send(4559491098)
    # print db.check_wxpay_hong_and_send(4559494038)
    # print db.check_wxpay_hong_and_send(4559512963)
    # print db.check_wxpay_hong_and_send(4559538181)
    # print db.check_wxpay_hong_and_send(4559612074)
    # print db.check_wxpay_hong_and_send(4559637595)
    # print db.check_wxpay_hong_and_send(4559748099)
    # print db.check_wxpay_hong_and_send(4559779961)
    # print db.check_wxpay_hong_and_send(4559906794)
    # print db.check_wxpay_hong_and_send(4560104264)
    # print db.check_wxpay_hong_and_send(4560161970)
    # print db.check_wxpay_hong_and_send(4560162107)
    # print db.check_wxpay_hong_and_send(4560179292)
    # print db.check_wxpay_hong_and_send(4560195305)
    # print db.check_wxpay_hong_and_send(4560205710)
    # print db.check_wxpay_hong_and_send(4560208704)
    # print db.check_wxpay_hong_and_send(4560219347)
    # print db.check_wxpay_hong_and_send(4560221945)
    # print db.check_wxpay_hong_and_send(4560225167)
    # print db.check_wxpay_hong_and_send(4560264221)
    # print db.check_wxpay_hong_and_send(4560269152)
    # print db.check_wxpay_hong_and_send(4560272333)
    # print db.check_wxpay_hong_and_send(4560277778)
    # print db.check_wxpay_hong_and_send(4560283849)
    # print db.check_wxpay_hong_and_send(4560305193)
    # print db.check_wxpay_hong_and_send(4560317324)
    # print db.check_wxpay_hong_and_send(4560317639)
    # print db.check_wxpay_hong_and_send(4560327620)
    # print db.check_wxpay_hong_and_send(4560354422)
    # print db.check_wxpay_hong_and_send(4560362776)
    # print db.check_wxpay_hong_and_send(4560363222)
    # print db.check_wxpay_hong_and_send(4560374342)
    # print db.check_wxpay_hong_and_send(4560379855)
    # print db.check_wxpay_hong_and_send(4560383367)
    # print db.check_wxpay_hong_and_send(4560412385)
    # print db.check_wxpay_hong_and_send(4560442115)
    # print db.check_wxpay_hong_and_send(4560443352)
    # print db.check_wxpay_hong_and_send(4560451901)
    # print db.check_wxpay_hong_and_send(4560465985)
    # print db.check_wxpay_hong_and_send(4560469321)
    # print db.check_wxpay_hong_and_send(4560479549)
    # print db.check_wxpay_hong_and_send(4560479717)
    # print db.check_wxpay_hong_and_send(4560481659)
    # print db.check_wxpay_hong_and_send(4560488214)
    # print db.check_wxpay_hong_and_send(4560524382)
    # print db.check_wxpay_hong_and_send(4560529564)
    # print db.check_wxpay_hong_and_send(4560545186)
    # print db.check_wxpay_hong_and_send(4560547694)
    # print db.check_wxpay_hong_and_send(4560623937)
    # print db.check_wxpay_hong_and_send(4560630370)
    # print db.check_wxpay_hong_and_send(4560632008)
    # print db.check_wxpay_hong_and_send(4560677487)
    # print db.check_wxpay_hong_and_send(4560685809)
    # print db.check_wxpay_hong_and_send(4560689845)
    # print db.check_wxpay_hong_and_send(4560703037)
    # print db.check_wxpay_hong_and_send(4560712243)
    # print db.check_wxpay_hong_and_send(4560775325)
    # print db.check_wxpay_hong_and_send(4560795219)
    # print db.check_wxpay_hong_and_send(4560803836)
    # print db.check_wxpay_hong_and_send(4560814894)
    # print db.check_wxpay_hong_and_send(4560841689)
    # print db.check_wxpay_hong_and_send(4560857604)
    # print db.check_wxpay_hong_and_send(4560880105)
    # print db.check_wxpay_hong_and_send(4560902822)
    # print db.check_wxpay_hong_and_send(4560911567)
    # print db.check_wxpay_hong_and_send(4560925668)
    # print db.check_wxpay_hong_and_send(4560930761)
    # print db.check_wxpay_hong_and_send(4561038786)
    # print db.check_wxpay_hong_and_send(4561054394)
    # print db.check_wxpay_hong_and_send(4561081709)
    # print db.check_wxpay_hong_and_send(4561146348)
    # print db.check_wxpay_hong_and_send(4561299903)
    # print db.check_wxpay_hong_and_send(4561338494)
    # print db.check_wxpay_hong_and_send(4561406089)

def testRedis():
    import redis
    redis_server = '127.0.0.1:6379'
    pool = redis.ConnectionPool(host=redis_server.split(':')[0], port=redis_server.split(':')[1], db=0, socket_connect_timeout=20)
    RedisCacher = redis.Redis(connection_pool=pool)
    RedisCacher.ping()
    RedisCacher.set('foo','bar')
    print RedisCacher.get('foo')
    return RedisCacher.dbsize()

if __name__ == "__main__":
    from models import mforweixin,mdb,mqsnaire,madmin,mqcloud
    from helpers import formatting

    # print formatting.json_string(f1216(),ensure_ascii=False)

    # mforweixin.test()

    # madmin.testSendQnaire('w767f9304cb111e79393e70a0ce84eda')

    # print mforweixin.sendLinkRTMessage('olJ2zuADCnfNFhGimO_6ggECTvTs', MSG_WELCOME)

    # print formatting.json_string(madmin.list_market())

    # print formatting.json_string(mqsnaire.sendPromoteSale())

    # if wxcode=='diaochadashi':
    #     printMemCacheDataByFSID(695423523,'ovZQXwHJuO1LPrgefXp-oV-FsWkg') #695423523在调查大师的openid
    # else:
    #     printMemCacheDataByFSID(695423523,'olJ2zuIjHKUyDLyWsu6y0ZkPvcdA') #695423523在test的openid
    # printMemCacheDataByFSID()

    # 同步static目录到COS
    # if mqcloud.cos_init('qsniare'):
    #     mqcloud.sync_upload_cos('static')

    # from helpers import formatting,utils
    # import json
    # print utils.get_random_number()

    # print utils.sendGetRequest('https://sojump.com/m/13327870.aspx')

    # print madmin.repairRedSend(3953371524)
    # time.sleep(5)

    f20180420()

