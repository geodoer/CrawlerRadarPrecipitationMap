# -*- coding: utf-8 -*-
# @Time    : 2019/4/7 10:27
# @Author  : PasserQi
# @Email   : passerqi@gmail.com
# @File    : log
# @Software: PyCharm
# @Version :
# @Desc    :

from tools import get_current_time
import os
import json
import logging

global logger
global cnt
global project_dir
global log_dir

def getlogger():
    global logger
    return logger

def init(_project_dir, _log_dir):
    global logger
    global cnt
    global project_dir
    global log_dir
    # get params
    cnt = 1
    project_dir = _project_dir
    log_dir = _log_dir
    # init log
    fp = os.path.join(log_dir,
        "[LOG] {}.txt".format(get_current_time())
    )
    logging.basicConfig()
    LEVEL = logging.DEBUG
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LEVEL)
    handler = logging.FileHandler(fp, encoding='utf-8')
    handler.setLevel(LEVEL)
    formatter = logging.Formatter('[%(asctime)s] - %(name)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    console = logging.StreamHandler()
    console.setLevel(LEVEL)
    logger.addHandler(handler)
    logger.addHandler(console)


def save_json(fn, obj):
    """ 将Python对象保存成JSON文件
    :param dir: 保存文件夹
    :param fn: 文件名，不包含.json
    :param obj: 对象
    :return:
    """
    global cnt
    global log_dir

    if log_dir is None:
        getlogger().error("LOG还未init")
        return None

    getlogger().info("【{}】{}".format(fn, obj) )
    fp = os.path.join(log_dir, "[{}] {}.json".format(cnt, fn))
    if os.path.exists(fp): #原来有，删掉
        os.remove(fp)
    with open(fp, 'w+') as f:
        json.dump(obj, f, indent=4)
        f.close()
        cnt += 1
    return fp