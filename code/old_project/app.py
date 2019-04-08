# coding:utf-8
# @Author:PasserQi
# @Version: v1.0.0 2019/3/17

from flask import Flask, render_template, request
from concurrent.futures import ThreadPoolExecutor
import webbrowser

import os
from tools import get_time
from tools import is_timestr
from tools import get_latlng
from tools import save_params_file
from tools import save_json
from collections import OrderedDict
from worker import start
from crawler import init_crawler

import sys
defaultencoding = 'utf-8'
if sys.getdefaultencoding() != defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)

app = Flask(__name__,
    static_url_path='' #将static路径该为/，文件正常引用
)
executor = ThreadPoolExecutor(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/initparam', methods=['post'])
def initparam():
    """ 初始化参数
    """
    params = OrderedDict()

    print "【从前端获得参数】 %s" % str(request.values)
    print "【正在处理参数】"   

    # 【开始时间】
    params["start_time"] = request.form.get("startTime", type=str)
    if is_timestr(params['start_time']) is False:
        params['start_time'] = get_time()
    print "\t[开始时间] %s" % params["start_time"]

    # 【结束时间】
    params["end_time"] = request.form.get("endTime", type=str)
    if is_timestr(params['end_time']) is False:
        params['end_time'] = "未设置" # 不结束
    print "\t[结束时间] %s" %params["end_time"]

    # 【时间间隔】
    params["interval"] = request.form.get("interval", type=int)
    params['step'] = params['interval'] / 5  # 步长
    print "\t[时间间隔] %d" % params["interval"]
    print "\t[保存图片的步长] %d" % params["step"]

    # 【处理点】
    points = {
        'center_point' : request.form.get("centerPoint", type=str),
        'north_west_point' : request.form.get("northWestPoint", type=str),
        'north_east_point' : request.form.get("northEastPoint", type=str),
        'south_east_point' : request.form.get("southEastPoint", type=str),
        'south_west_point' : request.form.get("southWestPoint", type=str)
    }
    print '\t[点] %s' % str(points)
    for point_name,value in points.items():
        params[point_name] = get_latlng(
            value
        )

    # 【保存文件夹】
    params["save_file_dir"] = request.form.get("saveFileDir", type=str)
    print "\t[保存文件夹] %s" % params["save_file_dir"]
    save_dir = params["save_file_dir"]
    if not os.path.exists(save_dir):
        # 选择的文件夹不存在
        print "\t【WARNING】 选择的文件夹不存在，跳转到初始页面"
        print "【params】" + str(params)
        return redirect_index("文件夹路径不存在，请重新输入！")
    # # 【输出文件夹】
    out_dir = os.path.join(save_dir, params['start_time'])
    params['out_dir'] = out_dir
    print "\t[图像输出文件夹] %s" % params["out_dir"]
    if os.path.exists(out_dir):
        # 输出文件夹已经存在
        print "【params】" + str(params)
        return redirect_index("输出文件夹已经存在，%s<Br/>请重新输入文件夹！" % out_dir)
    os.makedirs(out_dir)

    # 项目备注
    params["remark"] = request.form.get("remark")
    print "\t[项目备注] %s" % params["remark"]

    img_len, request_points = init_crawler(params) #计算每次请求的中心点
    print request_points
    if img_len==0:
        return "抱歉，任务失败！<br/>框选区域没有雷达降水图。"
    else:
        # 初始化文件夹
        init_dir(params, request_points)

        # 保存爬取参数
        print "【params】" + str(params)
        save_json(out_dir, u"0 param - 爬取参数", params) #保存成json
        file_str = save_params_file(params) #保存给用户看
        html_str = file_str.replace('\n', '<br/>') #输出的HTML字符串

        # 开启任务，异步进程
        executor.submit(
            start(params, request_points)
        )

        return '任务已在后台运行！<br/>每次需要爬取{}张图片！<br/>{}'.format(img_len, html_str)

def init_dir(params, request_points):
    project_dir = params["out_dir"]
    # original文件夹
    original_dir = os.path.join(project_dir, "0original")
    if os.path.exists(original_dir) is False:
        os.mkdir(original_dir)
    params["original_dir"] = original_dir

    # registration文件夹
    registration_dir = os.path.join(project_dir, "1registration_dir")
    if os.path.exists(registration_dir) is False:
        os.mkdir(registration_dir)
    params["registration_dir"] = registration_dir

    # mosaic
    mosaic_dir = os.path.join(project_dir, "2mosaic_dir")
    if os.path.exists(mosaic_dir) is False:
        os.mkdir(mosaic_dir)
    params["mosaic_dir"] = mosaic_dir

    # frame文件夹
    for frame,frame_value in request_points.items():
        # 原始数据
        frame_dir = os.path.join(original_dir, frame)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)
        # 配准数据
        frame_dir = os.path.join(registration_dir, frame)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)

def redirect_index(msg):
    """ 重定向到index，并且显示msg
    :param msg:
    :return:
    """
    return '''
        <html>
        <head>
            <title>CityWalker</title>
            <!-- 自动跳转-->
            <meta http-equiv="Refresh" content="5;url=http://127.0.0.1:5000/"/>
        </head>
        <body>
        %s<br/>5秒后为您自动跳转
        </body>
        </html>
    ''' % msg

if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:5000/', 0, False)
    app.run()