#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
    Author:cleverdeng
    E-mail:clverdeng@gmail.com
"""

__version__ = '0.9'
__all__ = ["PinYin"]

import os.path
mod_dir = os.path.dirname(os.path.realpath(__file__)) # 得到绝对路径

class PinYin(object):
    def __init__(self, dict_file=mod_dir+os.path.sep+'word.data'):
        self.word_dict = {}
        self.dict_file = dict_file

    def load_word(self):
        if not os.path.exists(self.dict_file):
            raise IOError("NotFoundFile")
        with file(self.dict_file) as f_obj:
            for f_line in f_obj.readlines():
                line = f_line.split()
                self.word_dict[line[0]] = line[1]

    def hanzi2pinyin(self, string=""):
        result = []
        if not isinstance(string, unicode):
            string = string.decode("utf-8")
        for char in string:
            key = '%X' % ord(char)
            result.append(self.word_dict.get(key, char).split()[0][:-1].lower())
        return result

    def hanzi2pinyin_split(self, string="", split=""):
        result = self.hanzi2pinyin(string=string)
        if split == "":
            return result
        else:
            return split.join(result)

    def sorted(self, iterable, key=lambda x:x):
        ''' 按拼音排序Unicode字符串序列，key参数指定获取元素unicode的函数 '''
        return sorted(iterable,
                    key=lambda x:tuple((self.word_dict.get('%X'%ord(c),c) for c in key(x))))

if __name__ == "__main__":
    test = PinYin()
    test.load_word()
    for s in test.sorted(list(u'一二三四五六七八九十')):
        print s
    for s in test.sorted([u'张三', u'张三丰', u'李四', u'王二', u'王大麻子', u'金二']):
        print s
    string = "钓鱼岛是中国的"
    print "in: %s" % string
    print "out: %s" % str(test.hanzi2pinyin(string=string))
    print "out: %s" % test.hanzi2pinyin_split(string=string, split="-")