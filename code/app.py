# -*- coding: utf-8 -*-
# @Time    : 2019/4/6 9:34
# @Author  : PasserQi
# @Email   : passerqi@gmail.com
# @File    : app.py
# @Software: PyCharm
# @Version : v2
# @Desc    :

# flask
from flask import Flask, render_template, request, jsonify
import webbrowser
from concurrent.futures import ThreadPoolExecutor


# data structure
from collections import OrderedDict
from crawler import get_frames

# Tools
import os
from tools import is_timestr
from tools import parse_latlngstr
from tools import get_current_time
from json import loads

import log

app = Flask(__name__,
    static_url_path='' #将static路径该为/，文件正常引用
)
executor = ThreadPoolExecutor(1)
global params

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/initparam', methods=['post'])
def initparam():
    global params
    # 处理params
    params = processing_params(request)
    if type(params) is not OrderedDict:
        # 出错
        return redirect_index(params)

    frame_len,frames = get_frames(params)
    if frame_len==0:
        return redirect_index("抱歉，任务失败！<br/>框选区域没有雷达降水图。")
    params["frames"] = frames

    return render_template('show_frame.html', frames=frames)

@app.route('/getframesinfo', methods=['post'])
def getframesinfo():
    global params
    ret = {
        "extent_gcj02" : params["extent_gcj02"],
        "frames" : params["frames"]
    }
    return jsonify({
        "result" : ret
    })

@app.route('/dowork', methods=['post'])
def dowork():
    global params

    # 图幅处理
    log.getlogger().info( "【前端返回】{}".format(request.values) )
    selected_frames_str = request.form.get("selected_frames", type=str)
    frames_selected = loads(selected_frames_str)
    params["frames_selected"] = frames_selected
    log.getlogger().info("【选择的图幅号】{}".format(frames_selected))
    for frame in params["frames"]:
        if frame in frames_selected:
            params["frames"][frame]["selected"] = "1"
        else:
            params["frames"][frame]["selected"] = "0"

    print("[DEBUG]{}".format(params))
    # 初始化文件夹
    init_dir()
    ret = save_params_file(params) #将参数保存至文件夹
    ret = ret.split("\n")

    return render_template('start.html', infos=ret)

from worker import start_work
@app.route('/start', methods=['post'])
def start():
    global params
    # 开启任务，异步进程
    executor.submit(
        start_work(params)
    )
    return "ok"

from worker import stop_work
@app.route('/stop', methods=['post'])
def stop():
    stop_work()
    return "ok"

def processing_params(request):
    """
    :param request:
    :return: params dict
    """
    print("【index.html提交的参数】{}".format(request.values))

    # ------- get params from form -------
    params = OrderedDict()
    params["create_time"] = get_current_time()
    params["start_time"] = request.form.get("startTime", type=str)      #开始时间
    params["end_time"] = request.form.get("endTime", type=str)          #结束时间
    params["interval"] = request.form.get("interval", type=int)         #时间间隔
    params["step"] = request.form.get("step", type=int)                 #步长
    params["points"] = {                                                #范围
        'center_point' : request.form.get("centerPoint", type=str),
        'north_west_point' : request.form.get("northWestPoint", type=str),
        'north_east_point' : request.form.get("northEastPoint", type=str),
        'south_east_point' : request.form.get("southEastPoint", type=str),
        'south_west_point' : request.form.get("southWestPoint", type=str)
    }
    params["save_file_dir"] = request.form.get("saveFileDir", type=str) #保存文件夹
    params["remark"] = request.form.get("remark")                       #项目备注

    # ------- processing -------
    # end_time
    if is_timestr(params["end_time"]) is False:
        params["end_time"] = "未设置"
    # extent
    for point_name,point_value in params["points"].items():
        params["points"][point_name] = parse_latlngstr(point_value)
    params["extent_gcj02"] = (
        params["points"]["south_west_point"][0],
        params["points"]["south_west_point"][1],
        params["points"]["north_east_point"][0],
        params["points"]["north_east_point"][1]
    )
    # save dir
    save_dir = params["save_file_dir"]
    if not os.path.exists(save_dir):
        # 选择的文件夹不存在
        return "【ERROR】输入的“保存文件夹”错误，路径不存在：{}。".format(save_dir)
    # project dir
    project_dir = os.path.join(save_dir, params["create_time"])
    if os.path.exists(project_dir):
        return "【ERROR】工程目录（{}）已存在，请重试！".format(project_dir)
    os.makedirs(project_dir)
    params["project_dir"] = project_dir
    # log dir
    params["log_dir"] = os.path.join(project_dir, "log")
    os.makedirs(params["log_dir"])
    log.init(params["project_dir"], params["log_dir"] )

    log.save_json("processing_params", params)
    return params

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

def init_dir():
    global params
    project_dir = params["project_dir"]

    # original文件夹
    original_dir = os.path.join(project_dir, "0original")
    if os.path.exists(original_dir) is False:
        os.mkdir(original_dir)
    params["original_dir"] = original_dir

    # registration文件夹
    registration_dir = os.path.join(project_dir, "1registration")
    if os.path.exists(registration_dir) is False:
        os.mkdir(registration_dir)
    params["registration_dir"] = registration_dir

    # mosaic
    mosaic_dir = os.path.join(project_dir, "2mosaic")
    if os.path.exists(mosaic_dir) is False:
        os.mkdir(mosaic_dir)
    params["mosaic_dir"] = mosaic_dir

    # frame文件夹
    for frame_num in params["frames_selected"]:
        # 原始数据
        frame_dir = os.path.join(original_dir, frame_num)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)
        # 配准数据
        frame_dir = os.path.join(registration_dir, frame_num)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)

    return True

def save_params_file(params):
    """ 将参数输出
    :param params:
    :return:
    """
    import os
    params_name = {
        "create_time" : "工程创建时间",
        "start_time": "爬取的开始时间",
        "end_time": '爬取的结束时间',
        "interval": '爬取的时间间隔（min）',
        "step" : "爬取的步长（°）",
        "points": '用户框选范围',
        'save_file_dir': '保存文件夹',
        "remark": "项目备注",
        "frames_selected" : "选择的图幅号",
        'project_dir' : '工程目录（图像输出文件夹）',
        "log_dir" : "日志文件夹",
        "original_dir" : "原始数据-GCJ02",
        "registration_dir" : "配准数据-WGS84",
        "mosaic_dir" : "镶嵌图-WGS84"
    }
    out_path = os.path.join(
        params["project_dir"], u'爬取参数.txt'
    )
    ret = "无特殊说明，坐标都为GCJ-02标准\n"
    with open(out_path, 'w+', encoding='utf-8') as fp:
        for param in params.keys():
            if param in params_name.keys():
                name = params_name[param]
                value = params[param]
                ret += '【' + str(name) + '】\t' + str(value) + '\n'
        fp.write(ret)
        fp.close()
    if ret=="":
        return "【ERROR】 保存初始参数时，出错"
    else:
        return ret

if __name__ == '__main__':
    webbrowser.open("http:\\127.0.0.1:5000")
    app.run()