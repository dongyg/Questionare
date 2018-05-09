#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys,os
app_root = os.path.dirname(__file__)

if app_root.strip()!='':
    sys.path.append(app_root)
    os.chdir(app_root)

from config import *

from web.wsgiserver import CherryPyWSGIServer
CherryPyWSGIServer.ssl_certificate = "ssl/2_dev.aifetel.cc.crt"
CherryPyWSGIServer.ssl_private_key = "ssl/3_dev.aifetel.cc.key"

import controllers.cpublic

urls = (
    #根路径需要放在最后面
    '',                 'seeroot',
    '/',                controllers.cpublic.app_urls
)

################################################################################
class seeroot:
    def GET(self):
        raise web.seeother('/')

################################################################################
# in production, we should disable the autoreload of the urls mapping
app = web.application(urls, globals(), autoreload = False)

# if web.config.get('_session') is None:
#     store = web.session.DBStore(dbFrame, 'sessions')
#     # store = web.session.DiskStore('sessions')
#     session = web.session.Session(app, store, initializer={'FSID':None,'OPENID':None})
#     web.config._session = session
# else:
#     session = web.config._session
# def session_hook():
#     web.ctx.session = session
# app.add_processor(web.loadhook(session_hook))

#使用Apache+WSGI方式部署时需要这句
application = app.wsgifunc()

if __name__ == "__main__":
    app.run()
