#!/usr/bin/env python
#-*- encoding: utf-8 -*-

#连接qcloud
#30515173 - COS(Cloud Object Service) - qsnaire

import json
import traceback
from qcloud_cos import *

cos_appid = 1252112172
cos_secret_id = u'AKID98vVr0Cd7SaVCgI1sVu52lHZeWAcBrfG' # 替换为用户的secret_id
cos_secret_key = u'UlodEclhPt9C1d1C9sNfjaDcomY6QWP4'    # 替换为用户的secret_key
cos_region_info = "sh"                                  # 替换为用户的region，例如 sh 表示华东园区, gz 表示华南园区, tj 表示华北园区
cos_bucket = u'qsnaire'
cos_client = CosClient(cos_appid, cos_secret_id, cos_secret_key, region=cos_region_info)

################################################################################
def cos_init(bucket):
    '''连接到指定bucket'''
    global cos_bucket
    if isinstance(bucket,str):
        bucket = bucket.decode('utf8')
    cos_bucket = bucket
    return cos_bucket!=u''

def cos_ls(folder=''):
    '''获取目录列表'''
    try:
        request = ListFolderRequest(cos_bucket, u'%s/'%folder)
        retval = cos_client.list_folder(request)
        return [x['name'] for x in retval['data']['infos']]
    except Exception, e:
        traceback.print_exc()
        return e

def cos_mkdir(folder):
    '''folder：cos路径, 必须从bucket下的根/开始，目录路径必须以/结尾, 例如 /mytest/dir/。错误返回消息，成功返回空'''
    try:
        request = CreateFolderRequest(cos_bucket, u'%s/'%folder)
        retval = cos_client.create_folder(request)
        if retval.get('code',999)!=0:
            return retval.get('message')
        else:
            return ''
    except Exception, e:
        traceback.print_exc()
        return e

def cos_rmdir(folder):
    '''删除目录'''
    try:
        request = DelFolderRequest(cos_bucket, u'/sample_folder/')
        delete_folder_ret = cos_client.del_folder(request)
        if retval.get('code',999)!=0:
            return retval.get('message')
        else:
            return ''
    except Exception, e:
        traceback.print_exc()
        return e

################################################################################
def cos_upload(filename):
    '''上传文件'''
    try:
        request = UploadFileRequest(cos_bucket, u'/%s'%filename.replace(u'\\',u'/'), filename, u'', 0)
        retval = cos_client.upload_file(request)
        if retval.get('code',999)!=0:
            return retval.get('message')
        else:
            return ''
    except Exception, e:
        traceback.print_exc()
        return e

def cos_delete(filename):
    '''删除文件'''
    try:
        request = DelFileRequest(cos_bucket, u'/%s'%filename.replace(u'\\',u'/'))
        retval = cos_client.del_file(request)
        if retval.get('code',999)!=0:
            return retval.get('message')
        else:
            return ''
    except Exception, e:
        traceback.print_exc()
        return e

################################################################################
def lsfiles(folder,exclude=['.DS_Store']):
    '''返回指定目录下的所有文件名列表，含子目录，文件名转成unicode字符串。返回字典：{文件名:[修改时间戳，大小，是否已上传],}'''
    allfiles = {}
    import os
    for root, dirs, files in os.walk(folder):
        for name in files:
            if name not in exclude:
                fn = os.path.join(root, name)
                if isinstance(fn,str):
                    fn = fn.decode('utf8')
                statinfo = os.stat(fn)
                allfiles[fn] = [round(statinfo.st_mtime,3),statinfo.st_size,False]
    return allfiles

def sync_files_cos(files,record_filename):
    '''同步指定文件到COS。record_filename为记录上传标记的文件名'''
    import marshal,os
    if isinstance(files,basestring):
        files = [files]
    #1.取本地存储的上传记录
    savfiles = {}
    if os.path.isfile(record_filename):
        fle = open(record_filename, 'rb')
        savfiles = marshal.load(fle)
        fle.close()
    #2.上传
    print 'Upload to COS ......'
    for fname in files:
        if isinstance(fname,str):
            fname = fname.decode('utf8')
        print fname,'......',
        if os.path.isfile(fname):
            statinfo = os.stat(fname)
            retup = cos_upload(fname)
            if not retup:
                savfiles[fname] = [round(statinfo.st_mtime,3),statinfo.st_size,1] #{文件名:[修改时间戳，大小，是否已上传]}
                print 'OK'
            else:
                print retup
                savfiles[fname] = [round(statinfo.st_mtime,3),statinfo.st_size,0] #{文件名:[修改时间戳，大小，是否已上传]}
        else:
            print 'not exists!'
    #3.保存上传结果
    if len(files)>0:
        fle = open(record_filename, 'wb')
        marshal.dump(savfiles,fle)
        fle.close()

def sync_upload_cos(folder,exclude=['.DS_Store']):
    '''同步指定本地目录的所有文件到COS。返回上传后的文件字典：{文件名:[修改时间戳，大小，是否已上传],}'''
    #COS不用建目录，直接上传会自动建目录
    import marshal,os
    if isinstance(folder,str):
        folder = folder.decode('utf8')
    #1.取指定目录所有文件
    allfiles = lsfiles(folder,exclude)
    print 'Local Files:',len(allfiles.keys())
    #2.取本地存储的上传记录
    savfiles = {}
    record_filename = u'%s_upto_cos_%s.rec'%(folder,cos_bucket)
    if os.path.isfile(record_filename):
        fle = open(record_filename, 'rb')
        savfiles = marshal.load(fle)
        fle.close()
    print 'Remote(mark) Files:',len(savfiles.keys())
    #3.与上传记录进行比较，取出需要上传的文件和要删除的文件。{文件名:[修改时间戳，大小，是否要执行上传],}
    needremove = []
    for fname,finfo in savfiles.items():
        if not allfiles.has_key(fname): #如果记录的已上传文件在本地不存在了，就删除
            needremove.append(fname)
    upcount = 0
    for fname,finfo in allfiles.items():
        state = savfiles.get(fname,[0,0,False])
        is_up = state[0]!=finfo[0] or state[1]!=finfo[1]
        upcount = upcount + (1 if is_up else 0)
        savfiles[fname] = [finfo[0],finfo[1],is_up]
    #4.执行上传和删除
    upok = 0
    upfail = 0
    if upcount>0:
        for fname,finfo in savfiles.items():
            if isinstance(finfo[2],bool) and finfo[2]==True:
                print fname,'......',
                retup = cos_upload(fname)
                if not retup:
                    savfiles[fname] = [finfo[0],finfo[1],1] #{文件名:[修改时间戳，大小，是否已上传]}
                    print 'OK'
                    upok += 1
                else:
                    print retup
                    savfiles[fname] = [finfo[0],finfo[1],0] #{文件名:[修改时间戳，大小，是否已上传]}
                    upfail += 1
    print 'Needs upload:',upcount,'  Success:',upok,'  Failed:',upfail
    #删除文件
    rmok = 0
    rmfail = 0
    for fname in needremove:
        print fname,'...Remove...',
        retrm = cos_delete(fname)
        if not retrm:
            savfiles.pop(fname,None)
            print 'OK'
            rmok += 1
        else:
            print retrm
            rmfail += 1
    print 'Needs remove:',len(needremove),'  Success:',rmok,'  Failed:',rmfail
    #5.保存上传结果
    if upcount>0 or len(needremove)>0:
        fle = open(record_filename, 'wb')
        marshal.dump(savfiles,fle)
        fle.close()
        print 'Upload mark',record_filename,'Saved.'
    print 'Done.'


################################################################################
def test_qcloud_cos_delete():
    '''测试COS删除'''
    import time
    appid = 1252112172                                  # 替换为用户的appid
    secret_id = u'AKID98vVr0Cd7SaVCgI1sVu52lHZeWAcBrfG' # 替换为用户的secret_id
    secret_key = u'UlodEclhPt9C1d1C9sNfjaDcomY6QWP4'    # 替换为用户的secret_key
    region_info = "sh"                                  # 替换为用户的region，例如 sh 表示华东园区, gz 表示华南园区, tj 表示华北园区
    cos_client = CosClient(appid, secret_id, secret_key, region=region_info)
    L = [u'avatar2.jpg']
    for x in L:
        time.sleep(0.1)
        request = DelFileRequest(u'qsnaire', u'/i3/static/%s'%x)
        del_ret = cos_client.del_file(request)
        print del_ret

################################################################################
if __name__ == "__main__":
    print 'Usage: sync_upload_cos(folder)'

