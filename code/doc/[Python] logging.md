【logging库】Python的一个标准库模块，一个灵活的事件日志系统

# 日志级别

1. 日志等级：DEBUG < INFO < WARNING < ERROR < CRITICAL，而日志的信息量是依次减少的
2. logging模块也可以指定日志记录器的日志级别，只有级别大于或等于该指定日志级别的日志记录才会被输出，小于该等级的日志记录将会被丢弃

|日志级别|描述|
|-|-|
|DEBUG|最详细的日志信息，典型应用场景是 问题诊断|
|INFO|信息详细程度仅次于DEBUG，通常只记录关键节点信息，用于确认一切都是按照我们预期的那样进行工作|
|WARNING|当某些不期望的事情发生时记录的信息（如，磁盘可用空间较低），但是此时应用程序还是正常运行的|
|ERROR|由于一个更严重的问题导致某些功能不能正常运行时记录的信息|
|CRITICAL|当发生严重错误，导致应用程序不能继续运行时记录的信息|

# 使用方法
【两种记录日志的方式】
1. 使用logging提供的模块级别的函数
2. 第二种是使用Logging日志系统的四大组件

# 使用例子
```python
import os
import json
import logging
import time

global logger
global cnt
global project_dir
global log_dir

TIME_FORMAT = "TIME_FORMAT = "%Y-%m-%d %H-%M-%S""

def getlogger():
    global logger
    return logger
    
def time_to_timestamp(t):
    return time.mktime(time.strptime(t, TIME_FORMAT))

def timestamp_to_time(c):
    return time.strftime(TIME_FORMAT, time.localtime(c) )

def get_current_time():
    """ 得到当前时间
    :return: 格式为TIME_FORMAT的时间
    """
    c = time.time()
    t = timestamp_to_time(c)
    return t

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
```



【参考文章】
1. https://www.cnblogs.com/yyds/p/6901864.html