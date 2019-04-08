# -*- coding: utf-8 -*-
# @Time    : 2019/4/6 9:46
# @Author  : PasserQi
# @Email   : passerqi@gmail.com
# @File    : tools
# @Software: PyCharm
# @Version : v1.0.0 2019/03/16
#            v2.0.0 2019/04/06
# @Desc    :

import time

TIME_FORMAT = "%Y-%m-%d %H-%M-%S"
RE_TIME_FORMAT = "^(\d{4}-\d{2}-\d{2}) (\d{2}-\d{2})$"


# 时间戳：是指格林威治时间1970年01月01日00时00分00秒(北京时间1970年01月01日08时00分00秒)起至现在的总秒数
def time_to_timestamp(t):
    """ 时间转换成时间戳
    :param t:
    :return:
    """
    return time.mktime(time.strptime(t, TIME_FORMAT))

def timestamp_to_time(c):
    """ 时间戳转成时间
    :param c:
    :return:
    """
    return time.strftime(TIME_FORMAT, time.localtime(c) )

def get_current_time():
    """ 得到当前时间
    :return: 格式为TIME_FORMAT的时间
    """
    c = time.time()
    t = timestamp_to_time(c)
    return t

def get_current_timestamp():
    """ 得到当前的时间戳
    :return:
    """
    return time.time()

def is_timestr(str):
    """ 检查是否为时间字符串
    :param str:
    :return:
    """
    import re
    result = re.match(RE_TIME_FORMAT, str)
    if result is None:
        return False
    else:
        return True


def parse_latlngstr(latlng_str):
    """ 从latlng字符串提取经纬度
    :param latlng_str:
    :return:
    """
    import re
    result = re.match('^LatLng\((.*)\)$', latlng_str)
    if result is None:
        return False
    latlng = result.group(1)
    lat,lng = latlng.split(',')
    return float(lat),float(lng)