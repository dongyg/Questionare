# -*- encoding=utf-8 -*-

# Author: Alex Ksikes

# - should be made into a class

try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
except ImportError:
    import Image, ImageDraw, ImageFont, ImageEnhance

import cStringIO, os, base64

def save(fi, filename, min_width=30, min_height=20, max_width=480, max_height=480, max_kb=40):
    im = get_image_object(fi)
    width, height = im.size

    if min_width <= width <= max_width and min_height <= height <= max_height:
        if len(fi) <= max_kb * 1024:
            if isinstance(filename,basestring):
                open(filename, 'wb').write(fi)
            else:
                filename.write(fi)
        else:
            compress(im, filename)
    else:
        thumbnail(im, filename, max_width, max_height)
        fsize = os.path.getsize(filename) if isinstance(filename,basestring) else len(filename)
        if fsize > max_kb * 1024:
            compress(im, filename)

def get_image_object(fi):
    if not isinstance(fi, file):
        fi = cStringIO.StringIO(fi)

    im = Image.open(fi)
    if im.mode != "RGB":
        im = im.convert("RGB")

    return im

def compress(im, out):
    im.save(out, format='jpeg')

def thumbnail(im, out, max_width, max_height):
    im.thumbnail((max_width, max_height), Image.ANTIALIAS)
    im.save(out, "PNG", quality=60) #png可以保证A通道


def compressImageWithBase64(imgB64,dst_w=0):
    '''输入：一个图像的base64编码。输出：把这个图像缩小后的base64编码'''
    fin = cStringIO.StringIO(base64.b64decode(imgB64))
    # fin = cStringIO.StringIO()
    # fin.write(base64.b64decode(imgB64))
    # fin.seek(0) # 文件读写指针归位
    img = Image.open(fin)
    fout = cStringIO.StringIO()
    thumbnail(img, fout, dst_w or 480, dst_w or 480)
    return base64.b64encode(fout.getvalue())

def resizeImageData(data,destw,desth,force=True):
    '''输入：一个图像的数据，要生成的图像的宽/高(为0表示以另一边为基准按比例缩放)，是否强制目标尺寸（即使源尺寸更小）。输出：resize后的图像数据'''
    if destw==0 and desth==0:
        return data
    fin = cStringIO.StringIO(data)
    img = Image.open(fin)
    width, height = img.size
    if not force:
        if destw!=0:
            destw = min(destw,width)
        if desth!=0:
            desth = min(desth,height)
        if destw==0:
            destw = int(desth/float(height) * width)
        if desth==0:
            desth = int(destw/float(width) * height)
    if destw!=width or desth!=height:
        fout = cStringIO.StringIO()
        img.thumbnail((destw, desth), Image.ANTIALIAS)
        img.save(fout, "jpeg", quality=80)
        return fout.getvalue()
    else:
        return data



