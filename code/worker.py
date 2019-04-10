# -*- coding: utf-8 -*-
# @Time    : 2019/4/8 21:17
# @Author  : PasserQi
# @Email   : passerqi@gmail.com
# @File    : worker
# @Software: PyCharm
# @Version :
# @Desc    :
import os
import shutil

from osgeo import ogr
from osgeo import osr
from osgeo import gdal
from coordinate_conversion import gcj02towgs84_extent
import log

from tools import is_timestr
from tools import time_to_timestamp
from tools import get_current_timestamp
from tools import timestamp_to_time
from tools import get_current_time
from crawler import do_get
from collections import OrderedDict
from crawler import download_file
import json
from PIL import Image
from tools import floatrange
from gdal_merge import main_by_params


# =================================================
# 定时任务
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
sched = BlockingScheduler()
# 监听器
def listener(event):
    if event.exception:
        log.getlogger().info("【{}任务退出】{}".format(event.job_id, event.exception.message))
    else:
        log.getlogger().info( "【爬取任务正常运行】")
sched.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


global params
global original_data
original_data = OrderedDict()
    # {
    #     "0,0" : { #图幅名
    #         "2019-03-31 17-49-00" : { #时间
    #             "time" : "",          #时间
    #             "timestamp" : "",     #时间戳
    #             "url" : "",           #下载链接
    #             "extent" : "",        #范围
    #             "req_pnt" : "",       #该瓦片请求的点坐标
    #             "file_path" : ""      #文件的path
    #         },
    #         ...
    #     },
    #     ...
    # }
global registration_data
registration_data = OrderedDict()
    # {
    #     "0,0" : { #图幅名
    #        "2019-03-31 17-49-00" : { #时间
    #             {
    #                 "extent" : "", #范围-WGS84
    #                 "file_path" : "", #该文件的路径
    #             }
    #        }
    #     },
    #     ...
    # }
global mosaic_data
mosaic_data = OrderedDict()
# {
#     "2019-04-09 19-00-00": { #时间线上的时间戳
#         "time": "none", #融合后的名字
#         "file_path": "none", #融合后的路径
#         "subimgs": { #子图
#             "2019-04-09 18-58-00": { #时间
#                 "extent": [ #范围WGS84
#                     23.001399080910634,
#                     114.90128470887859,
#                     27.133925327023302,
#                     119.46273202573005
#                 ],
#                 "file_path": "D:\\mycode\\CrawlerRadarPrecipitationMap\\tmp\\2019-04-09 20-39-47\\1registration\\1,1\\1,1 2019-04-09 18-58-00.tif",
#                 "frame_num": "1,1", #图幅号
#                 "time": "2019-04-09 18-58-00" #时间
#             },
#         }
#     }, ....
# }
def start_work(_params):
    global params
    params = _params

    # 转坐标
    params["extent_wgs84"] = gcj02towgs84_extent(params["extent_gcj02"])
    d = params["frames"].copy()  # 防止遍历出异常错误
    for frame_num, frame_value in d.items():
        params["frames"][frame_num]["extent_wgs84"] = gcj02towgs84_extent(frame_value["extent_gcj02"])
    log.save_json("params-wgs84", params)

    # 将图幅保存成shp文件
    save_to_shp()

    # 结束时间
    end_time = params["end_time"]
    if is_timestr(end_time):
        # 设置了结束时间
        end_timestrap = time_to_timestamp(end_time)  # 转换为时间戳好比较时间
        end_timestrap += 1 * 60 * 60  # 结束时间点上的img需要之后1h小时才能爬取
    else:
        # 没有设置结束时间
        end_timestrap = None
    params["end_timestrap"] = end_timestrap

    # 开始爬取
    loop()  # 立即调用一次
    sched.start()  # 开始定时任务
    pass

def stop_work():
    sched.shutdown()

# =================================================
# 定时任务
@sched.scheduled_job('interval', hours=1) #1h爬一次
def loop():
    global params
    global original_data
    frames = params["frames"]
    frames_selected = params["frames_selected"]
    end_timestrap = params["end_timestrap"]
    current_timestrap = get_current_timestamp()
    current_time = timestamp_to_time(current_timestrap)

    if end_timestrap is not None: #有设置结束时间
        if current_timestrap>end_timestrap:
            log.getlogger().info("【结束】到达结束时间，停止爬取")
            sched.shutdown()

    log.getlogger().info("【开始爬取】{}".format(current_time) )

    for frame_num in frames_selected:
        # 要爬取的图幅
        req_pnt = frames[frame_num]["req_pnt"]
        imgs = do_get(*req_pnt)
        if imgs is None:
            log.getlogger().error("图幅{}出错：在该位置上没有获取到imgs".format(frame_num))
            continue
        # 处理imgs
        for img in imgs:
            timestrap = img[1]
            time = timestamp_to_time(timestrap)
            # 加入数据
            if frame_num not in original_data:
                original_data[frame_num] = OrderedDict()
            if time not in original_data[frame_num]:
                original_data[frame_num][time] = {
                    "timestamp": timestrap,
                    "time": time,
                    "url": img[0],
                    "extent_gcj02": img[2],
                    "req_pnt": req_pnt,
                    "file_path": ""
                }
            else:
                pass

    log.getlogger().info("原始数据：{}".format(original_data) )
    log.save_json("original_data-{}".format(time), original_data)

    download() #下载
    registration()  # 配准
    mosaic() #融合
    return

# ==================================================================
# 下载数据
def download():
    global params
    global original_data

    log.getlogger().info("【下载数据】")

    original_dir = params["original_dir"]
    d = original_data.copy() #防止出错
    for frame,frame_value in d.items():
        # 保存文件夹
        frame_dir = os.path.join(original_dir, frame)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)

        for time,time_value in frame_value.items():
            if time_value["file_path"]!="":
                # 已下载
                continue

            # 下载
            url = time_value["url"]
            fn, fp = download_file(url, frame_dir)
            if fn==None: #下载错误
                log.getlogger().error("【下载失败】{}".format(url) )
                continue
            else: #下载完成
                time_value["file_path"] = fp
                time_value["file_name"] = fn
                # 保存头文件
                hdr_fn = os.path.splitext(fn)[0] #头文件名称
                save_hdr(frame_dir, hdr_fn, time_value)

    log.getlogger().info("\t下载数据结束")
    pass

# ==================================================================
# 配准数据
def registration():
    global params
    global original_data
    global registration_data
    registration_dir = params["registration_dir"]
    current_time = get_current_time()

    log.getlogger().info("【配准数据】")

    d = original_data.copy() #防止异常错误
    for frame,frame_value in d.items():
        for time,time_value in frame_value.items():
            # 原始数据
            original_file_path = time_value["file_path"]
            if original_file_path=="":
                # 还没有下载
                continue
            original_file_name = time_value["file_name"]

            # 配准数据
            if frame not in registration_data:
                registration_data[frame] = OrderedDict()

            if time in registration_data:
                # 该数据已经配准过了
                continue

            # 该数据还没有配准
            registration_file_name = "{} {}.tif".format(frame, time) #tif格式
            frame_path = os.path.join(registration_dir, frame)
            registration_file_path = os.path.join(frame_path, registration_file_name)
            if os.path.exists(registration_file_path) is True:
                # 该数据已经存在
                continue

            rgs_data_item = do_rgs(time_value, registration_file_path)
            if rgs_data_item is None:
                log.getlogger().error("[配准失败！] {}".format(original_file_path) )
            else:
                # 配准完成，保存到data_rgs
                registration_data[frame][time] = rgs_data_item
                params["timeline_endtime"] = time #把时间保存下来，当前配准的最后一个数据的时间

    log.save_json("registration_data_{}".format(current_time), registration_data)
    pass

def do_rgs(data_time_value, rgs_file_path):
    """ 配准
    :param data_time_value: dict 原始图像的信息-GCJ02
        {
            "time" : "",          #时间
            "timestamp" : "",     #时间戳
            "url" : "",           #下载链接
            "extent" : "",        #范围
            "req_pnt" : "",       #该瓦片请求的点坐标
            "file_path" : ""      #文件的path
        }
    :param rgs_file_path: str 配准后保存的路径
    :return: rgs_data_item: dict/None
        {
            "extent" : "", #范围-WGS84
            "file_path" : "", #该文件的路径
        }
    """
    # 将tiff保存到配准文件夹
    origin_file_path = data_time_value["file_path"]
    im = Image.open(origin_file_path)
    im.save(rgs_file_path)

    # 转换extent
    extent_gcj02 = data_time_value["extent_gcj02"] #[21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]
    extent_wgs84 = gcj02towgs84_extent(extent_gcj02) #[21.53519080438208, 115.14078044126353, 25.66805217057752, 119.65050502755392]
    x1, y1, x2, y2 = extent_wgs84

    # 用extent_wgs84对rgs_file_path文件进行配准
    ds = gdal.Open(rgs_file_path, gdal.GA_Update) #打开影像
    if not ds:
        return None
    # 创建坐标系
    srs = osr.SpatialReference()
    srs.SetWellKnownGeogCS('WGS84')
    # 相关信息
    rows = ds.RasterYSize  # 行数
    cols = ds.RasterXSize  # 列数

    # 创建地面控制点：经度、纬度、z，照片列数，照片行数
    gcps = [
        gdal.GCP(y1, x2, 0, 0, 0),  # 左上
        gdal.GCP(y2, x2, 0, cols-1, 0),  # 右上
        gdal.GCP(y1, x1, 0, 0, rows-1),  # 左下
        gdal.GCP(y2, x1, 0, cols - 1, rows - 1)  # 右下
    ]
    ds.SetGCPs(gcps, srs.ExportToWkt())
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform(gdal.GCPsToGeoTransform(gcps))
    del ds

    return {
        "extent" : extent_wgs84,
        "file_path" : rgs_file_path
    }


# ==================================================================
# 融合数据
def mosaic():
    global params
    global registration_data
    global mosaic_data

    # 结束时间
    timeline_endtime = params["timeline_endtime"]
    timeline_endtime_stamp = time_to_timestamp(timeline_endtime)
    # 开始时间
    start_time = "{}-00".format( params["start_time"] )
    timeline_starttime_stamp = time_to_timestamp(start_time)
    # 时间间隔
    interval = params["interval"] * 60  # 秒数
    # 遍历
    for timeline_time_stamp in floatrange(timeline_starttime_stamp, timeline_endtime_stamp, interval):
        timeline_time = timestamp_to_time(timeline_time_stamp) #时间线上的时间

        if timeline_time in mosaic_data:
            # 这个时间点数据已经融合
            continue
        # 融合
        mosaic_item = do_mosaic(timeline_time)
        if type(mosaic_item) is dict:
            mosaic_data[timeline_time] = mosaic_item
            log.getlogger().info("【融合】{}时间的数据已处理完成。".format(timeline_time))
        else:
            log.getlogger().info("【融合】出错。")

    log.save_json("mosaic_data_{}".format(get_current_time() ), mosaic_data)
    pass

def do_mosaic(timeline_time):
    """ 找到timeline_time前面的一个图幅们
    :param timeline_time: 时间线上的时间
    :return: dict
        time 实际时间（文件名）
        file_path 文件路径
        subimgs 子图像
    """
    global params
    global registration_data
    frame_selected = params["frames_selected"]
    mosaic_dir = params["mosaic_dir"] #融合的文件夹

    timeline_time_stamp = time_to_timestamp(timeline_time) #时间线上的点：时间戳格式
    # log.getlogger().info("[融合] 时间线上的时间戳{}".format(timeline_time) )

    subimgs = {} #子图像
    d = registration_data.copy() #防止异常报错
    for frame_num,frame_value in d.items():
        log.getlogger().info("[融合] - 找图幅{}的图片".format(frame_num) )
        # 在每个图幅中找一个timeline_time_stamp最近的图片
        prior_time = None
        for time,time_value in frame_value.items():
            timestamp = time_to_timestamp(time) #转成时间戳
            if timestamp>timeline_time_stamp:
                # 找到了，即为prior_time
                if prior_time is None:
                    # 出错了，没有找到timeline_time前面的数据
                    log.getlogger().error("[融合] -- 没有找到{}前面的数据".format(frame_num, timeline_time))
                    return None
                # log.getlogger().info("[融合] -- 找到了{}".format(prior_time) )
                subimgs[prior_time] = frame_value[prior_time]
                subimgs[prior_time]["frame_num"] = frame_num
                subimgs[prior_time]["time"] = prior_time
                continue
            else:
                prior_time = time

    # log.getlogger().info("[融合] - 找到的图片{}".format(subimgs) )
    if len(subimgs)!=len(frame_selected):
        # 出错了，没有找到这么多幅图片
        log.getlogger().info("[融合] - 所找图片不够，当前只找到{}".format(len(subimgs)) )
        return None

    if len(subimgs)==1: #只有一幅图
        for timeline_time,time_value in subimgs.items():
            last_time = time_value["time"]
            reg_file_path = time_value["file_path"] #配准数据位置
            mosaic_file_path = os.path.join(mosaic_dir, "{}.tif".format(last_time) )
            shutil.copyfile(reg_file_path, mosaic_file_path)
            return {
                "time": last_time,
                "file_path": mosaic_file_path
            }
    else: #多幅图
        # 将subimgs排序
        times = []
        for time in subimgs.keys():
            times.append(time_to_timestamp(time) )
        times.sort() #排序
        # 存放到subimgs
        new_subimgs = OrderedDict()
        for timestamp in times:
            time = timestamp_to_time(timestamp)
            new_subimgs[time] = subimgs[time]

        # 对new_subimgs（时间顺序）进行融合
        last_time = None
        reg_file_paths = [] #配准图片
        for timeline_time,time_value in new_subimgs.items():
            last_time = time_value["time"]
            reg_file_paths.append(time_value["file_path"] )
        mosaic_file_path = os.path.join(mosaic_dir, "{}.tif".format(last_time))
        # 对reg_file_paths按顺序进行拼接，并存储到mosaic_file_path
        main_by_params({
            "-o" : mosaic_file_path,
            "input_files" : reg_file_paths
        })
        return {
            "time": last_time,
            "file_path": mosaic_file_path,
            "subimgs": new_subimgs
        }


# ===================================================================
# | Tools
def save_hdr(dir, fn, obj):
    import os
    fp = os.path.join(dir, fn + '.json')
    if os.path.exists(fp):  # 原来有，删掉
        os.remove(fp)
    with open(fp, 'w+') as f:
        json.dump(obj, f, indent=4)
        f.close()
    return fp

def save_to_shp():
    # 本函数的参数设置
    shp_name = "frames"

    global params
    project_dir = params["project_dir"]

    # 驱动
    driver = ogr.GetDriverByName("ESRI Shapefile")
    # 文件路径
    shp_dir = os.path.join(project_dir, "{}_shp".format(shp_name) )
    os.makedirs(shp_dir)
    shp_path = os.path.join(shp_dir, "{}.shp".format(shp_name) )
    if os.access(shp_path, os.F_OK):
        # 若存在，删除
        driver.DeleteDataSource(shp_path)
    # 数据源
    ds = driver.CreateDataSource(shp_path)  # 创建shp文件
    # 坐标系
    srs = osr.SpatialReference()
    srs.SetWellKnownGeogCS('WGS84')
    # 图层
    layer = ds.CreateLayer(name=shp_path,
       srs=srs,
       geom_type=ogr.wkbPolygon,
       options=[  # 设置编码
           "ENCODING=UTF-8"
       ]
    )
    # 字段
    # # name字段
    fieldcnstr = ogr.FieldDefn("name", ogr.OFTString)  # 创建字段(字段名，类型)
    fieldcnstr.SetWidth(20)  # 设置宽度
    layer.CreateField(fieldcnstr)  # 将字段设置到layer
    # # 是否选择
    fieldcnstr = ogr.FieldDefn("selected", ogr.OFTString)  # 创建字段(字段名，类型)
    fieldcnstr.SetWidth(10)  # 设置宽度
    layer.CreateField(fieldcnstr)  # 将字段设置到layer

    # 要素
    feat = ogr.Feature(layer.GetLayerDefn())

    # 用户框选区域
    x1, y1, x2, y2 = params["extent_wgs84"]
    # 将许多个点，打包成points。但是一定要注意，点要顺时针
    points = [ # 顺时针
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
        [x1, y1]
    ]
    ring = ogr.Geometry(ogr.wkbLinearRing)  # 环
    polygon = ogr.Geometry(ogr.wkbPolygon)  # 创建面
    for point in points:
        ring.AddPoint(point[1], point[0])  # 经度，纬度
    polygon.AddGeometry(ring)  # 将环加入面
    polygon.CloseRings()  # 首尾关闭
    feat.SetGeometry(polygon)  # 将Geometry给feature
    feat.SetField('name', "用户框选区域")  # 设置字段值
    feat.SetField("selected", "null")
    layer.CreateFeature(feat)  # 并将Feature加入图层

    # 图层范围
    d = params["frames"].copy() #防止异常报错
    for frame_num, frame_value in d.items():
        ring = ogr.Geometry(ogr.wkbLinearRing)  # 环
        polygon = ogr.Geometry(ogr.wkbPolygon)  # 创建面

        x1, y1, x2, y2 = frame_value["extent_wgs84"]
        points = [  # 顺时针
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2],
            [x1, y1]
        ]
        for point in points:
            ring.AddPoint(point[1], point[0])  # 经度，纬度
        polygon.AddGeometry(ring)  # 将环加入面
        polygon.CloseRings()  # 首尾关闭
        feat.SetGeometry(polygon)  # 将Geometry给feature
        feat.SetField('name', frame_num)  # 设置图幅号
        feat.SetField('selected', frame_value["selected"]) # 设置是否选择
        layer.CreateFeature(feat)  # 并将Feature加入图层

    ds.Destroy()
    return True