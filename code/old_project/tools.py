# coding:utf8
# @Author:PasserQi
# @Version: v1.0.0 2019/3/16
import time
import json


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

def get_time():
    """ 得到当前时间
    :return: 格式为TIME_FORMAT的时间
    """
    c = time.time()
    t = timestamp_to_time(c)
    return t

def get_timestamp():
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

def get_time_dt(str):
    import re
    result = re.match(RE_TIME_FORMAT, str)
    if result is None:
        return False
    d = result.group(1)
    t = result.group(2)
    return d, t

def get_latlng(latlng_str):
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

def save_params_file(params):
    """ 将参数输出
    :param params:
    :return:
    """
    import os
    params_name = {
        "start_time": "开始时间",
        "end_time": '结束时间',
        "interval": '时间间隔',
        "center_point": '中心点坐标',
        'north_west_point': '左上角坐标',
        'north_east_point': '右上角坐标',
        'south_east_point': '右下角坐标',
        'south_west_point': '左下角坐标',
        'save_file_dir': '保存文件夹',
        'out_dir' : '工程目录（图像输出文件夹）',
        "remark" : "项目备注",
        "original_dir" : "原始数据-GCJ02",
        "registration_dir" : "配准数据-WGS84",
        "mosaic_dir" : "镶嵌图-WGS84"
    }
    out_path = os.path.join(
        params["out_dir"], u'爬取参数.txt'
    )
    ret = "无特殊说明，坐标都为GCJ-02标准\n"
    with open(out_path, 'w+') as fp:
        for param in params.keys():
            if param in params_name.keys():
                name = params_name[param]
                value = params[param]
                ret += '【' + str(name) + '】\t' + str(value) + '\n'
        # for key,name in params_name.items():
        #     fp.write( '[' + str(name) + ']\t' + str(params[key]) + '\n' )
        fp.write(ret)
        fp.close()
    if ret=="":
        return "【ERROR】 保存初始参数时，出错"
    else:
        return ret

global logger
def get_log(dir, fn=""):
    """ 初始化日志
    按fp获取日志对象
    :param dir：文件夹
    :param fn： 文件名（可选）
    :return: logger
    """
    import logging
    from os.path import join

    logging.basicConfig()
    if fn=="":
        fn = "[LOG] %s.txt" % str(get_time() )
    fp = join(dir, fn)

    LEVEL = logging.DEBUG
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LEVEL)
    handler = logging.FileHandler(fp)
    handler.setLevel(LEVEL)
    formatter = logging.Formatter('[%(asctime)s] - %(name)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    console = logging.StreamHandler()
    console.setLevel(LEVEL)
    logger.addHandler(handler)
    logger.addHandler(console)

    return logger


def save_json(dir, fn, obj):
    """ 将Python对象保存成JSON文件
    :param dir:
    :param fn:
    :param obj:
    :return:
    """
    import os
    fp = os.path.join(dir, fn + '.json')
    if os.path.exists(fp): #原来有，删掉
        os.remove(fp)
    with open(fp, 'w+') as f:
        json.dump(obj, f, indent=4)
        f.close()
    return fp



if __name__ == '__main__':
    # print is_timestr("2019-03-16 19-52-20")
    # print get_latlng('LatLng(24.485274, 118.095131)')


    # logger = get_log('C:\Users\PasserQi\Desktop\2.txt')
    # logger.info("Start print log")
    # logger.debug("Do something")
    # logger.warning("Something maybe fail.")
    # logger.info("Finish")
    data = {"1": "2"}
    save_json(r"C:\Users\PasserQi\Desktop\tmp", "9 data", data)
    data["2"] = "2"
    save_json(r"C:\Users\PasserQi\Desktop\tmp", "9 data", data)

    pass