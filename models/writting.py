#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *

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
        ws0.write(row,1,opt['QI_TITLE'].decode('utf8'), styleNormal)
    #答卷页
    dict_option = dict([(x.QI_NO,json.loads(x.QI_OPTION) for x in option)])
    ws1 = workbook.add_sheet(u'答卷')
    answer = dbFrame.select("QN_ANSWERS",vars=locals(),where="QN_ID=$qnid",order="ANSWER_NO").list()
    ws1.write(0,0,u'序号', styleNormal)
    ws1.write(0,1,u'答卷时间', styleNormal)
    ws1.write(0,2,u'用户IP', styleNormal)
    for idx,opt in enumerate(option,1):
        ws1.write(0,2+idx,u'Q%d'%idx, styleNormal)
    for row,ans in enumerate(answer,1):
        ws1.write(row,0,row, styleNormal)
        ws1.write(row,1,ans['INPUT_TIME'].decode('utf8'), styleNormal)
        ws1.write(row,2,ans['CLIENTIP'].decode('utf8'), styleNormal)
        ancontent = json.loads(ans['AN_CONTENT'])
        for col,val in enumerate(ancontent,3):
            title = dict_option.get(val,u'').decode('utf8')
            ws1.write(row,col,title, styleNormal)
    #保存
    fakefile = StringIO()
    workbook.save(fakefile)
    retval = fakefile.getvalue()
    fakefile.close()
    return retval
