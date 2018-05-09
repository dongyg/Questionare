# -*- coding: utf-8 -*-
# 全局配置、全局常量、全局变量、全局引入包，所有系统级的东西都在这里做好，业务py里面就直接from config import *而不再import支撑方面的东西

#TODO: 有需要完善的功能
#VARIANT: 有配置数据，例如微信支付手续费的费率
#PS: 特别注释提醒
#DEBUG: 为了测试临时注释掉的内容或修改的内容

#全局常量
db_host = '127.0.0.1'
db_port = 3306
db_name = 'qsnaire'
db_user = 'root'
db_pass = '123456'
db_type = 'mysql'
cacher_fans_obj = None
cacher_fsid_byopenid = None
cacher_random_checker = None
cacher_naire_sent = None
cacher_message_pool = None

#使用apache部署时，需要将当前目录添加到path中imprt web才不会出错
import os,sys
app_root = os.path.dirname(__file__)
if app_root.strip()!='':
    sys.path.append(app_root)
    os.chdir(app_root)

#全局导入包
import web
import urlparse
import json, uuid, datetime, time, hashlib, traceback, random, threading, string
from helpers import utils, image
from helpers import formatting
from helpers.factory import *
import ConfigParser

global mutex
mutex = threading.Lock()

#读配置数据
def getCfgParser(cfgFilename=''):
    cfgParser = ConfigParser.ConfigParser()
    if not cfgFilename:
        if len(sys.argv)==3 and sys.argv[2]:
            cfgname = sys.argv[2]
            cfgFilename = os.path.join(app_root,cfgname)
            if not os.path.isfile(cfgFilename):
                cfgFilename = os.path.join(app_root,'config.ini')
        else:
            cfgFilename = os.path.join(app_root,'config.ini')
    if not os.path.isfile(cfgFilename):
        cfgFilename = os.path.join(app_root,'configSample.ini')
    # print 'Use config file: ',cfgFilename
    cfgParser.read(cfgFilename)
    return cfgParser
cfgParser = getCfgParser()
#要想控制台就不输出sql语句，config.debug放在创建db前面
db_pass = cfgParser.get('Database', 'db_pass')
web.config.debug = cfgParser.getboolean('Environment', 'debug')
web.config.debug_sql = cfgParser.getboolean('Environment', 'debug_sql')
web.config.memcache_host = cfgParser.get('Environment', 'memcache_host')
web.config.redis_host = cfgParser.get('Environment', 'redis_host')
web.config.cache_mode = cfgParser.get('Environment', 'cache_mode')
web.config.host_http = cfgParser.get('Environment', 'host_http')
web.config.host_https = cfgParser.get('Environment', 'host_https')
web.config.weixincode = cfgParser.get('Environment', 'weixincode')

web.config.email_errors = ''
web.config.session_parameters['timeout'] = 60*60*24*3600

#数据库连接
dbFrame = web.database(dbn='mysql', host=db_host, port=db_port, db=db_name, user=db_user, passwd=db_pass)
cache = False
render_globals = utils.get_all_functions(formatting)
view_render = web.template.render(os.path.join(app_root, 'views'), cache=not web.config.debug, globals=render_globals)
admin_render = web.template.render(os.path.join(app_root, 'views', 'admin'), cache=not web.config.debug, globals=render_globals)

################################################################################
#微信公众平台相关
HOST_SSL = web.config.host_https
HOST_NOS = web.config.host_http
# MSG_WELCOME = {"title":"问卷调查大师欢迎你", "url":"%s/about"%HOST_NOS, "description":"在这里你即能发问卷也能答问卷\n1.有奖问卷，可以带图文描述，发问卷的同时还能宣传产品\n2.红包问卷，让你玩问卷的时候还能抢红包\n闲暇时间快来答问卷抽大奖/抢红包！\n详情猛击“查看全文”"}
MSG_WELCOME = "问卷调查大师欢迎你！您已获赠100调查币，可点击【我的调查币】菜单查看详情！"
MENUS = {
  "button": [
    {
      "name": "答问卷",
      "sub_button": [
        { "name": "先看说明", "type": "view", "url": "http://mp.weixin.qq.com/s/FqZr-unnJEn_xlYURxLfhg" },
        { "name": "答互助问卷", "type": "click", "key": "MA1" },
        { "name": "答有奖问卷", "type": "click", "key": "M10" },
        { "name": "答红包问卷", "type": "click", "key": "M11" },
        { "name": "我答过的问卷", "type": "click", "key": "M12" },
      ]
    },
    {
      "name": "发问卷",
      "sub_button": [
        { "name": "先看说明", "type": "view", "url": "http://mp.weixin.qq.com/s/SbYos2XY4KHhaDViQsFN9A" },
        { "name": "推广计划", "type": "view", "url": "http://mp.weixin.qq.com/s/_xm_DkgfKGXEnt4FXyO5ig" },
        # { "name": "创建有奖问卷", "type": "click", "key": "M20" },
        # { "name": "创建红包问卷", "type": "click", "key": "M21" },
        # { "name": "创建普通问卷", "type": "click", "key": "M22" },
        { "name": "从模板创建问卷", "type": "click", "key": "MB3" },
        { "name": "创建空白问卷", "type": "click", "key": "MB4" },
        { "name": "我发布的问卷", "type": "click", "key": "M23" },
      ]
    },
    {
      "name": "用户中心",
      "sub_button": [
        { "name": "签到", "type": "click", "key": "MC1" },
        { "name": "我的调查币", "type": "click", "key": "MC2" },
        { "name": "中奖和红包记录", "type": "click", "key": "M13" },
        { "name": "我的信息", "type": "click", "key": "M31" },
        { "name": "帮助中心", "type": "view", "url": "%s/faq"%HOST_NOS },
      ]
    }
  ]
}

wxcode = web.config.weixincode
wxaccount = web.Storage({
    "ORIGINAL_ID": 'gh_c450d6f36741',
    "APPID": 'wxaa70b76f1dcc6401',
    "APPSECRET": '3722f877c77ac618a127791e3eb34f6d',
    "TOKEN": 'dongyg_Aifetel',
    "ACCESSTOKEN": 'I8xEhdF0W98piBKGFWewDZ_51r2NzFwrRDd58x7_FaRXRTQhLga-1ZI3A8xebXSRXzijLSXzPSaNccF7Q7N_HbrwYh0BhoXVsR-WbKSqfyELLTaAAAZZH',
    "EXPIRES": 1481476841,
    "JSAPI_TICKET": "",
    "JSAPI_EXPIRES": 0,
    "WEBTOKEN": '',
    "WEBEXPIRES": 0,
    "MCH_ID": "",
    "WXPAY_KEY": "",
    "MENUS": json.dumps(MENUS, ensure_ascii=False)
})

################################################################################
#全局函数
def get_render(view,inpath):
    """获取指定view下的页面模板，inpath为模板页面路径；autoSuffix指示是否根据浏览器代理自动添加后缀"""
    kind, path = view._lookup(inpath)
    if path and kind in ('file','pyc'):
        return getattr(view, inpath)
    else:
        return None
def put_static_host(pagedata):
    if web.ctx.protocol=='https':
        pagedata['static_host'] = web.config.app_configuration.get('sys:static_host_https','')
    else:
        pagedata['static_host'] = web.config.app_configuration.get('sys:static_host_http','')

def read_wexin(weixincode):
    '''从数据库读取微信公众号账户信息'''
    global wxaccount
    m = web.listget(dbFrame.select("WX_ACCOUNT",vars=locals(),where='WEIXIN_CODE=$weixincode').list(),0)
    if m:
        m.MENUS = json.dumps(MENUS, ensure_ascii=False)
        print '-'*20,'Read WX Account [%s].'%weixincode
        wxaccount.ORIGINAL_ID = m.ORIGINAL_ID.encode('utf8')
        wxaccount.APPID = m.APPID.encode('utf8')
        wxaccount.APPSECRET = m.APPSECRET.encode('utf8')
        wxaccount.TOKEN = m.TOKEN.encode('utf8') if m.TOKEN else ''
        wxaccount.ACCESSTOKEN = m.ACCESSTOKEN.encode('utf8') if m.ACCESSTOKEN else ''
        wxaccount.EXPIRES = m.EXPIRES
        wxaccount.JSAPI_TICKET = m.JSAPI_TICKET
        wxaccount.JSAPI_EXPIRES = m.JSAPI_EXPIRES
        wxaccount.WEBTOKEN = m.WEBTOKEN.encode('utf8') if m.WEBTOKEN else ''
        wxaccount.WEBEXPIRES = m.WEBEXPIRES
        wxaccount.MCH_ID = m.MCH_ID.encode('utf8') if m.MCH_ID else ''
        wxaccount.WXPAY_KEY = m.WXPAY_KEY.encode('utf8') if m.WXPAY_KEY else ''
def read_config():
    '''从数据库表QN_CONFIGURATION中读取配置数据'''
    backconf = dict([(x['CFG_KEY'],x['CFG_VAL']) for x in dbFrame.select("QN_CONFIGURATION").list()])
    if 'app_configuration' not in web.config:
        web.config.app_configuration = {}
    web.config.app_configuration.update(backconf)
    m = dbFrame.select("WX_QRCODE",where="IS_SALER=1 or IS_ADMIN=1").list()
    web.config.app_configuration['run:saler'] = [x.BUSI_ID for x in m if x.IS_SALER==1]
    web.config.app_configuration['run:selfman'] = [x.BUSI_ID for x in m if x.IS_ADMIN==1]
    web.config.app_configuration['sys:blacklist'] = json.loads(web.config.app_configuration.get('sys:blacklist','[]'))
    web.config.app_configuration['run:blacklist'] = web.config.app_configuration['sys:blacklist'] + web.config.app_configuration.get('run:blacklist',[])
    web.config.sysenv_debug = bool(web.config.app_configuration.get('sys:debug',web.config.debug))
    #每日抢推广名额的互斥变量，默认是没有名额的，每天日结时重置
    web.config.today_apply = web.config.app_configuration.get('run:today_apply','')
    web.config.today_apply = json.loads(web.config.today_apply) if web.config.today_apply else []

################################################################################
def InitSystem():
    '''初始化系统运行'''
    global cacher_fans_obj, cacher_fsid_byopenid, cacher_random_checker, cacher_naire_sent, cacher_message_pool
    storage = {}
    if web.config.cache_mode=='memcached':
        import memcache
        storage = memcache.Client([web.config.memcache_host],debug=0)
        if not bool(storage.get_stats()):
            storage = {}
        if storage:
            print '-'*20,'MemCached'
            cacher_fans_obj = MemCacherFSOBJ(storage)
            cacher_fsid_byopenid = MemCacherOPENID(cacher_fans_obj,storage)
            cacher_naire_sent = MemCacherNaireSent(storage)
            cacher_random_checker = MemCacherRandomChecker(storage)
            cacher_message_pool = MemCacherMessagePool(storage)
    elif web.config.cache_mode=='redis':
        redis_server = web.config.redis_host
        try:
            import redis
            pool = redis.ConnectionPool(host=redis_server.split(':')[0], port=redis_server.split(':')[1], db=0, socket_connect_timeout=20)
            storage = redis.Redis(connection_pool=pool)
            storage.ping()
        except Exception, e:
            traceback.print_exc()
            storage = {}
        if storage:
            print '-'*20,'Redis'
            cacher_fans_obj = RedisCacherFSOBJ(storage)
            cacher_fsid_byopenid = RedisCacherOPENID(cacher_fans_obj,storage)
            cacher_naire_sent = RedisCacherNaireSent(storage)
            cacher_random_checker = RedisCacherRandomChecker(storage)
            cacher_message_pool = RedisCacherMessagePool(storage)
    if not storage:
        print '-'*20,'PyCached'
        cacher_fans_obj = PyCacherFSOBJ()
        cacher_fsid_byopenid = PyCacherOPENID(cacher_fans_obj)
        cacher_naire_sent = PyCacherNaireSent()
        cacher_random_checker = PyCacherRandomChecker()
        cacher_message_pool = PyCacherMessagePool()
    import models.mqsnaire
    models.mqsnaire.startTaskDaily()

################################################################################
read_config()
read_wexin(wxcode)

