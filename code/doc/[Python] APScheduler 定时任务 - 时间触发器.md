【定时任务】
1. 设置指定时间，到时间时执行相关操作
2. 时间触发器
3. 定时执行计划任务


【Python实现定时任务】方法介绍：https://www.cnblogs.com/yudis/articles/9790035.html?tdsourcetag=s_pctim_aiomsg

1. sleep
2. threading模块中的timer
3. sched内置模块
4. APScheduler定时框架


【sched文档】https://docs.python.org/2/library/sched.html
【APScheduler文档】https://apscheduler.readthedocs.io/en/latest/userguide.html


# APScheduler
【安装】
1. `pip install apscheduler`
2. 源码：https://pypi.python.org/pypi/APScheduler/

## 示例一：定时任务，到指定时间时退出
【结果】![在这里插入图片描述](https://img-blog.csdnimg.cn/20190331162611318.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3N1bW1lcl9kZXc=,size_16,color_FFFFFF,t_70)

```python
# coding:utf8
# func:
# 1. 程序运行打印时间
# 2. 程序间隔10秒打印时间
# 3. 到达指定时间时，结束程序

import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_SCHEDULER_SHUTDOWN

TIME_FORMAT = "%Y-%m-%d %H-%M-%S"
def get_current_time(): #得到当前时间
    return time.strftime(TIME_FORMAT, time.localtime(time.time()))
def time_to_timestamp(t): #时间转换成时间戳
    return time.mktime(time.strptime(t, TIME_FORMAT))


sched = BlockingScheduler()

# 监听器：判断是否正常运行
def my_listener(event):
    if event.exception:
        print "【程序退出】{}".format(event.exception.message)
        print "退出时间{}".format(get_current_time() )
    else:
        print '任务照常运行...'
sched.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_SCHEDULER_SHUTDOWN)

# 任务
cnt =0
@sched.scheduled_job(trigger="interval", args=("[定时调用]", ), seconds=10, id="print_time")
def print_time(param):
    global cnt

    current_time = get_current_time()
    current_timestampe = time_to_timestamp(current_time)
    end_timestampe = time_to_timestamp(end_time)
    if current_timestampe>end_timestampe: #到指定时间关闭程序
        sched.shutdown()
    else:
        print("{} {} {}".format(param, cnt, current_time) )

    cnt += 1
    pass

end_time = "2019-3-31 16-24-00"
if __name__ == '__main__':
    print_time("[函数调用]") #立刻先打印一次时间
    sched.start() #开始定时任务，10秒之后再打印
    pass
```


【参考文章】
1. https://www.cnblogs.com/luxiaojun/p/6567132.html