# -*- coding: utf-8 -*-

__all__ = ['PyCacherFSOBJ', 'PyCacherOPENID', 'PyCacherMessagePool', 'PyCacherNaireSent', 'PyCacherRandomChecker',
    'MemCacherFSOBJ', 'MemCacherOPENID', 'MemCacherMessagePool', 'MemCacherNaireSent', 'MemCacherRandomChecker',
    'RedisCacherFSOBJ', 'RedisCacherOPENID', 'RedisCacherMessagePool', 'RedisCacherNaireSent', 'RedisCacherRandomChecker',
    'printMemCacheDataByFSID', 'province_city'
    ]

import utils, json

province_city = {
    u"北京":["东城","西城","崇文","宣武","朝阳","丰台","石景山","海淀","门头沟","房山","通州","顺义","昌平","大兴","怀柔","平谷","密云","延庆"],
    u"天津":["和平","河东","河西","南开","河北","红桥","塘沽","汉沽","大港","东丽","西青","津南","北辰","武清","宝坻","宁河","静海","蓟县"],
    u"河北":["石家庄","唐山","秦皇岛","邯郸","邢台","保定","张家口","承德","沧州","廊坊","衡水"],
    u"山西":["太原","大同","阳泉","长治","晋城","朔州","晋中","运城","忻州","临汾","吕梁"],
    u"内蒙古":["呼和浩特","包头","乌海","赤峰","通辽","鄂尔多斯","呼伦贝尔","巴彦淖尔","乌兰察布","兴安","锡林郭勒","阿拉善"],
    u"辽宁":["沈阳","大连","鞍山","抚顺","本溪","丹东","锦州","营口","阜新","辽阳","盘锦","铁岭","朝阳","葫芦岛"],
    u"吉林":["长春","吉林","四平","辽源","通化","白山","松原","白城","延边"],
    u"黑龙江":["哈尔滨","齐齐哈尔","鸡西","鹤岗","双鸭山","大庆","伊春","佳木斯","七台河","牡丹江","黑河","绥化","大兴安岭"],
    u"上海":["黄浦","卢湾","徐汇","长宁","静安","普陀","闸北","虹口","杨浦","闵行","宝山","嘉定","浦东新区","金山","松江","青浦","南汇","奉贤","崇明县"],
    u"江苏":["南京","无锡","徐州","常州","苏州","南通","连云港","淮安","盐城","扬州","镇江","泰州","宿迁"],
    u"浙江":["杭州","宁波","温州","嘉兴","湖州","绍兴","金华","衢州","舟山","台州","丽水"],
    u"安徽":["合肥","芜湖","蚌埠","淮南","马鞍山","淮北","铜陵","安庆","黄山","滁州","阜阳","宿州","巢湖","六安","亳州","池州","宣城"],
    u"福建":["福州","厦门","莆田","三明","泉州","漳州","南平","龙岩","宁德地"],
    u"江西":["南昌","景德镇","萍乡","九江","新余","鹰潭","赣州","吉安","宜春","抚州","上饶"],
    u"山东":["济南","青岛","淄博","枣庄","东营","烟台","潍坊","济宁","泰安","威海","日照","莱芜","临沂","德州","聊城","滨州","菏泽"],
    u"河南":["郑州","开封","洛阳","平顶山","安阳","鹤壁","新乡","焦作","濮阳","许昌","漯河","三门峡","南阳","商丘","信阳","周口","驻马店"],
    u"湖北":["武汉","黄石","十堰","宜昌","襄樊","鄂州","荆门","孝感","荆州","黄冈","咸宁","随州","恩施"],
    u"湖南":["长沙","株洲","湘潭","衡阳","邵阳","岳阳","常德","张家界","益阳","郴州","永州","怀化","娄底","湘西"],
    u"广东":["广州","韶关","深圳","珠海","汕头","佛山","江门","湛江","茂名","肇庆","惠州","梅州","汕尾","河源","阳江","清远","东莞","中山","潮州","揭阳","云浮"],
    u"广西":["南宁","柳州","桂林","梧州","北海","防城港","钦州","贵港","玉林","百色","贺州","河池","来宾","崇左"],
    u"海南":["海口","三亚"],
    u"重庆":["万州","涪陵","渝中","大渡口","江北","沙坪坝","九龙坡","南岸","北碚","万盛","双桥","渝北","巴南","黔江","长寿","綦江","潼南","铜梁","大足","荣昌","璧山","梁平","城口","丰都","垫江","武隆","忠县","开县","云阳","奉节","巫山","巫溪","石柱","秀山","酉阳","彭水","江津","合川","永川","南川"],
    u"四川":["成都","自贡","攀枝花","泸州","德阳","绵阳","广元","遂宁","内江","乐山","南充","眉山","宜宾","广安","达州","雅安","巴中","资阳","阿坝","甘孜","凉山"],
    u"贵州":["贵阳","六盘水","遵义","安顺","铜仁","黔西南","毕节","黔东南","黔南"],
    u"云南":["昆明","曲靖","玉溪","保山","昭通","丽江","思茅","临沧","楚雄","红河","文山","西双版纳","大理","德宏","怒江","迪庆"],
    u"西藏":["拉萨","昌都","山南","日喀则","那曲","阿里","林芝"],
    u"陕西":["西安","铜川","宝鸡","咸阳","渭南","延安","汉中","榆林","安康","商洛"],
    u"甘肃":["兰州","嘉峪关","金昌","白银","天水","武威","张掖","平凉","酒泉","庆阳","定西","陇南","临夏","甘南"],
    u"青海":["西宁","海东","海北","黄南","海南","果洛","玉树","海西"],
    u"宁夏":["银川","石嘴山","吴忠","固原","中卫"],
    u"新疆":["乌鲁木齐","克拉玛依","吐鲁番地","哈密","昌吉","博尔塔拉","巴音郭楞","阿克苏","克孜勒苏","喀什","和田","伊犁","塔城","阿勒泰"],
}

################################################################################
#缓存：将来可以替换为MemCached
#缓存用户对象，key为FS_ID，value为用户对象
class PyCacherFSOBJ:
    def __init__(self,storage={}):
        self.storage = storage
    def get(self,fsid):
        self.cleanup()
        return self.storage.get(str(fsid))
    def set(self,fsid,value):
        self.storage[str(fsid)] = value
    def delete(self,fsid):
        return self.storage.pop(str(fsid),None)
    def cleanup(self):
        #缓存中保留1个小时的用户
        self.storage = dict([(k,v) for k,v in self.storage.items() if v and utils.calc_pastseconds(v.UNSUBSCRIBETIME)<3600])
    def count(self):
        return len(self.storage.keys())
class MemCacherFSOBJ:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'FSOBJ_'
    def get(self,fsid):
        retval = self.storage.get(self.prefix+str(fsid))
        import web
        return web.Storage(json.loads(retval)) if retval else None
    def set(self,fsid,value):
        self.storage.set(self.prefix+str(fsid),json.dumps(value,cls=utils.DateTimeJSONEncoder))
    def delete(self,fsid):
        return self.storage.delete(self.prefix+str(fsid))
class RedisCacherFSOBJ:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'FSOBJ_'
    def get(self,fsid):
        retval = self.storage.get(self.prefix+str(fsid))
        import web
        return web.Storage(json.loads(retval)) if retval else None
    def set(self,fsid,value):
        self.storage.set(self.prefix+str(fsid),json.dumps(value,cls=utils.DateTimeJSONEncoder))
    def delete(self,fsid):
        return self.storage.delete(self.prefix+str(fsid))

#缓存用户openid:fsid映射，get/set/delete时取fsid后再操作PyCacherFSOBJ
class PyCacherOPENID:
    def __init__(self,objcacher,storage={}):
        self.storage = storage
        self.objcacher = objcacher
    def get(self,openid):
        fsid = self.storage.get(openid)
        return self.objcacher.get(fsid) if fsid else None
    def getFSID(self,openid):
        #只返回fsid
        return self.storage.get(openid)
    def set(self,openid,value):
        if value and value.FS_ID:
            self.storage[openid] = value.FS_ID
            self.objcacher.set(value.FS_ID,value)
    def delete(self,openid):
        fsid = self.storage.pop(openid,None)
        return self.objcacher.delete(fsid) if fsid else None
class MemCacherOPENID:
    def __init__(self,objcacher,storage):
        self.objcacher = objcacher
        self.storage = storage
        self.prefix = 'OPENID_'
    def getFSID(self,openid):
        #只返回fsid
        return self.storage.get(self.prefix+openid)
    def get(self,openid):
        fsid = self.getFSID(self.prefix+openid)
        return self.objcacher.get(fsid) if fsid else None
    def set(self,openid,value):
        if value and value.FS_ID:
            self.storage.set(self.prefix+openid, value.FS_ID)
            self.objcacher.set(value.FS_ID,value)
    def delete(self,openid):
        fsid = self.getFSID(self.prefix+openid)
        self.storage.delete(self.prefix+openid)
        self.objcacher.delete(fsid)
class RedisCacherOPENID:
    def __init__(self,objcacher,storage):
        self.storage = storage
        self.prefix = 'OPENID_'
        self.objcacher = objcacher
    def getFSID(self,openid):
        #只返回fsid
        retval = self.storage.get(self.prefix+openid)
        if retval and retval.isdigit():
            retval = long(retval)
        return retval
    def get(self,openid):
        fsid = self.getFSID(self.prefix+openid)
        return self.objcacher.get(fsid) if fsid else None
    def set(self,openid,value):
        if value and value.FS_ID:
            self.storage.set(self.prefix+openid, value.FS_ID)
            self.objcacher.set(value.FS_ID,value)
    def delete(self,openid):
        fsid = self.getFSID(self.prefix+openid)
        self.storage.delete(self.prefix+openid)
        self.objcacher.delete(fsid)

################################################################################
#缓存每个问卷已经发送过给哪些粉丝 {qnid:set([fsid,fsid])}
#测试过，当qnid的set有100万元素时，in或not in操作判断是否在set中用时也不到0.01秒
class PyCacherNaireSent:
    def __init__(self,storage={}):
        self.storage = storage
    def get(self,qnid):
        return self.storage.get(qnid,set([]))
    def set(self,qnid,fsid):
        if not self.storage.has_key(qnid):
            self.storage[qnid] = set([])
        self.storage[qnid].add(fsid)
    def add(self,fsid,qnids):
        for qnid in qnids:
            self.set(qnid,fsid)
    def cleanup(self):
        self.storage = {}
    def dumps(self):
        import marshal
        fle = open('cacher_naire_sent.dat', 'wb')
        marshal.dump(self.storage,fle)
        fle.close()
    def loads(self):
        import marshal,os
        if os.path.isfile('cacher_naire_sent.dat'):
            fle = open('cacher_naire_sent.dat', 'rb')
            self.storage = marshal.load(fle)
            fle.close()
class MemCacherNaireSent:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'SENTQN_'
    def get(self,qnid):
        retval = self.storage.get(self.prefix+qnid)
        return set(json.loads(retval)) if retval else set([])
    def set(self,qnid,fsid):
        curr = self.get(qnid)
        curr.add(fsid)
        self.storage.set(self.prefix+qnid,json.dumps(list(curr)))
    def cleanup(self):
        pass
class RedisCacherNaireSent:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'SENTQN_'
    def get(self,qnid):
        retval = self.storage.get(self.prefix+qnid)
        return set(json.loads(retval)) if retval else set([])
    def set(self,qnid,fsid):
        curr = self.get(qnid)
        curr.add(fsid)
        self.storage.set(self.prefix+qnid,json.dumps(list(curr)))
    def cleanup(self):
        pass

################################################################################
#为每个用户缓存一个随机值，在打开页面(随机值在url参数中)、提交数据(随机值在页面hidden中作为post数据提交)等操作的时候，校验用户随机值以验证请求合法性
#为用户发送图文消息所带的url需要生成并添加随机值参数。为用户返回页面时需要生成并将随机值作为hidden域放在页面表单中
class PyCacherRandomChecker:
    def __init__(self,storage={}):
        self.storage = storage
    def __str__(self):
        retval = sorted(self.storage.iteritems(), key=lambda d:d[1], reverse = True)
        return '\n'.join(['%s : %s'%(x[1],x[0]) for x in retval])
        # return json.dumps(retval,ensure_ascii=False,indent=4)
    def genRandomValueForFSID(self,fsid):
        self.cleanup()
        retval = self.storage.get(str(fsid),'')
        if not retval:
            retval = utils.get_time18()+utils.get_random_string()
            self.storage[str(fsid)] = retval
        return retval
    def getRandomValueForFSID(self,fsid):
        retval = self.storage.get(str(fsid),None)
        return retval
    def popRandomValueForFSID(self,fsid):
        retval = self.storage.pop(str(fsid),None)
        return retval
    def chkRandomValueWithPop(self,fsid,r):
        return self.popRandomValueForFSID(fsid)==r and r!=None and r!=''
    def chkRandomValueNotPop(self,fsid,r):
        return self.getRandomValueForFSID(fsid)==r and r!=None and r!=''
    def dumps(self):
        import marshal
        fle = open('cacher_request_random.dat', 'wb')
        marshal.dump(self.storage,fle)
        fle.close()
    def loads(self):
        import marshal,os
        if os.path.isfile('cacher_request_random.dat'):
            fle = open('cacher_request_random.dat', 'rb')
            self.storage = marshal.load(fle)
            fle.close()
    def cleanup(self):
        #缓存随机数保存1个小时
        self.storage = dict([(k,v) for k,v in self.storage.items() if utils.calc_pastseconds(v)<3600])
class MemCacherRandomChecker:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'RANDOM_'
    def genRandomValueForFSID(self,fsid):
        retval = self.getRandomValueForFSID(fsid)
        if not retval:
            retval = utils.get_time18()+utils.get_random_string()
            self.storage.set(self.prefix+str(fsid),retval,time=3600) #随机数1个小时超时
        return retval
    def getRandomValueForFSID(self,fsid):
        return self.storage.get(self.prefix+str(fsid))
    def popRandomValueForFSID(self,fsid):
        retval = self.getRandomValueForFSID(fsid)
        self.storage.delete(self.prefix+str(fsid))
        return retval
    def chkRandomValueWithPop(self,fsid,r):
        return self.popRandomValueForFSID(fsid)==r and r!=None and r!=''
    def chkRandomValueNotPop(self,fsid,r):
        return self.getRandomValueForFSID(fsid)==r and r!=None and r!=''
class RedisCacherRandomChecker:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'RANDOM_'
    def genRandomValueForFSID(self,fsid):
        retval = self.getRandomValueForFSID(fsid)
        if not retval:
            retval = utils.get_time18()+utils.get_random_string()
            self.storage.set(self.prefix+str(fsid),retval) #Redis不支持缓存超时设置
        return retval
    def getRandomValueForFSID(self,fsid):
        return self.storage.get(self.prefix+str(fsid))
    def popRandomValueForFSID(self,fsid):
        retval = self.getRandomValueForFSID(fsid)
        self.storage.delete(self.prefix+str(fsid))
        return retval
    def chkRandomValueWithPop(self,fsid,r):
        return self.popRandomValueForFSID(fsid)==r and r!=None and r!=''
    def chkRandomValueNotPop(self,fsid,r):
        return self.getRandomValueForFSID(fsid)==r and r!=None and r!=''

################################################################################
class PyCacherMessagePool:
    def __init__(self,storage={}):
        self.storage = storage
    def __str__(self):
        return json.dumps(self.storage)
    def get(self,fsid):
        return self.storage.get(str(fsid))
    def pop(self,fsid):
        return self.storage.pop(str(fsid),'')
    def set(self,fsid,value):
        self.storage[str(fsid)] = value
class MemCacherMessagePool:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'MESSAGE_'
    def get(self,fsid):
        return self.storage.get(self.prefix+str(fsid))
    def pop(self,fsid):
        retval = self.get(fsid)
        self.storage.delete(self.prefix+str(fsid))
        return retval
    def set(self,fsid,value):
        self.storage.set(self.prefix+str(fsid),value)
class RedisCacherMessagePool:
    def __init__(self,storage):
        self.storage = storage
        self.prefix = 'MESSAGE_'
    def get(self,fsid):
        return self.storage.get(self.prefix+str(fsid))
    def pop(self,fsid):
        retval = self.get(fsid)
        self.storage.delete(self.prefix+str(fsid))
        return retval
    def set(self,fsid,value):
        self.storage.set(self.prefix+str(fsid),value)

################################################################################
def printMemCacheDataByFSID(fsid='',openid='',qnid='',mcserver='127.0.0.1:11211'):
    '''打印指定的memcached数据。可输入：fsid,openid,qnid'''
    import memcache
    mc = memcache.Client([mcserver],debug=0)
    if fsid or openid or qnid:
        print mc.get('FSOBJ_'+str(fsid))
        print mc.get('OPENID_'+openid)
        print mc.get('SENTQN_'+qnid)
        print mc.get('RANDOM_'+str(fsid))
        print mc.get('MESSAGE_'+str(fsid))
    stat = mc.get_stats()
    if len(stat)>0:
        if len(stat[0])>1:
            for k,v in stat[0][1].items():
                if k in ('bytes','curr_items','total_items','threads','limit_maxbytes','cmd_get','version'):
                    print k,v
        else:
            print stat
    else:
        print stat


