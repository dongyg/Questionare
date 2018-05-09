# -*- coding: utf-8 -*-

from HTMLParser import HTMLParser
from htmlentitydefs import entitydefs

class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_fed_data(self):
        return ''.join(self.fed)

def strip(html):
    """Strip html and will also remove entities."""
    s = HTMLStripper()
    s.feed(html)
    return s.get_fed_data()

class TitleParser(HTMLParser):

    def __init__(self):
        #定义要搜寻的标签
        self.handledtags = {'title':[],'div':['toptitle','divDesc','divQuestion']}  #提出标签，理论上可以提取所有标签的内容
        self.processing = None
        HTMLParser.__init__(self)  #继承父类的构造函数

    def handle_starttag(self,tag,attrs):
        #判断是否在要搜寻的标签内
        if tag in self.handledtags.keys():
            self.data = ''
            for attr in attrs:
                if attr[1] in self.handledtags[tag] or not self.handledtags[tag]:
                    self.processing = tag

    def handle_data(self,data):
        if self.processing:
            self.data += data

    def handle_endtag(self,tag):
        if tag == self.processing:
            print str(tag)+' : '+str(self.data)
            self.processing = None

    #下面两个函数都是对html实体做的转码，没有深究
    def handle_entityref(self,name):
        if entitydefs.has_key(name):
            self.handle_data(entitydefs[name])
        else:
            self.handle_data('&'+name+';')

    def handle_charref(self,name):
        try:
            charnum=int(name)
        except ValueError:
            return
        if charnum<1 or charnum>255:
            return
        self.handle_data(chr(charnum))

