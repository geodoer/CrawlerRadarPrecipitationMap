# coding:utf8
# @Author:PasserQi
# @Version: v1.0.0 2019/3/16


from tools import is_timestr
from tools import time_to_timestamp
from tools import get_timestamp
from tools import timestamp_to_time
from tools import save_json
from crawler import do_get
from crawler import download_file
import os

# 图像配准
from PIL import Image
from coordinate_conversion import gcj02towgs84
import gdal
import osr
# ogr
from osgeo import ogr

# log
from tools import get_log
global logger

# debug
from collections import OrderedDict

# ------------ 定时任务 ------------
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
sched = BlockingScheduler()
# 监听器
def listener(event):
    if event.exception:
        global data
        global project_dir
        logger.info("【{}任务退出】{}".format(event.job_id, event.exception.message))
        logger.info("【data】{}".format(data))
        save_json(project_dir, "9 data", data)

    else:
        logger.info( "【爬取任务正常运行】")
sched.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


# ------------ 全局变量 ------------
global params           #工程参数
global project_dir      #工程目录
global logger           #日志
global request_points   #请求的中心点坐标
global end_timestrap    #结束时间戳
global data             #original数据集
data = OrderedDict()
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
global data_rgs         #registration数据集
data_rgs = OrderedDict()
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

# ------------ 工作入口 ------------
def start(_params, req_points):
    """ 开始工作
    :param params:
    :param request_points: dict
        key : 图幅号 例"0,0"
        value : dict
            req_pnt: (x,y) 请求点
            extent : 范围
                extent is None 该请求点没有图幅
    :return:
    """
    global params
    params = _params

    global logger
    logger = get_log(params["out_dir"] )
    logger.info("【进程】开始下载")

    # 工程目录
    global project_dir
    project_dir = params["out_dir"]

    # 请求的中心点坐标
    global request_points
    request_points = req_points

    # 结束时间
    global end_timestrap
    end_time = params["end_time"]
    if is_timestr(end_time):
        #设置了结束时间
        end_timestrap = time_to_timestamp(end_time) #转换为时间戳好比较时间
        end_timestrap += 1*60*60 #结束时间点上的img需要之后1h小时才能爬取
    else:
        #没有设置结束时间
        end_timestrap = None

    save_to_shp()  # 将范围保存成shp

    # 开始爬取
    loop() #立即调用一次
    sched.start() # 开始定时任务
    return

# ------------ 定时任务 ------------
@sched.scheduled_job('interval', hours=1) #1h爬一次
def loop():
    # 检查是否到时间
    global end_timestrap
    global request_points
    current_timestamp = get_timestamp()
    if end_timestrap is not None: #有设置结束时间
        if current_timestamp>end_timestrap:
            sched.shutdown()

    current_time = timestamp_to_time(current_timestamp)
    logger.info("【开始爬取】{}".format(current_time) )

    # 爬取工作
    global data
    for frame,value in request_points.items():
        if value["extent"] is None: #该图幅没有img
            continue
        req_pnt = value["req_pnt"]
        imgs = do_get(*req_pnt)
        if imgs is None:
            logger.error("图幅{}出错：在该位置上没有获得imgs".format(frame) )
            continue
        # 处理imgs
        for img in imgs:
            timestamp = img[1] #时间戳
            time = timestamp_to_time(timestamp) #时间
            # 加入数据
            if frame not in data:
                data[frame] = OrderedDict()
            if time not in data[frame]:
                data[frame][time] = {
                    "timestamp" : timestamp,
                    "time" : time,
                    "url" : img[0],
                    "extent" : img[2],
                    "req_pnt" : req_pnt,
                    "file_path" : ""
                }
            else:
                pass
    print data

    save_json(project_dir, "9 data", data)

    download() #下载
    registration() #配准
    return

def save_to_shp():
    global params
    global request_points
    global project_dir
    shp_name = "frame"
    # 驱动
    driver = ogr.GetDriverByName("ESRI Shapefile")
    # 文件路径
    shp_path = os.path.join(project_dir, "{}.shp".format(shp_name) )
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
    fieldcnstr = ogr.FieldDefn("name", ogr.OFTString)  # 创建字段(字段名，类型)
    fieldcnstr.SetWidth(20)  # 设置宽度
    layer.CreateField(fieldcnstr)  # 将字段设置到layer
    # 要素
    feat = ogr.Feature(layer.GetLayerDefn())

    # 用户框选区域
    north_west_point = gcj02towgs84(params["north_west_point"][1], params["north_west_point"][0])  # 左上
    north_east_point = gcj02towgs84(params["north_east_point"][1], params["north_east_point"][0])  # 右上
    south_east_point = gcj02towgs84(params["south_east_point"][1], params["south_east_point"][0])  # 右下
    south_west_point = gcj02towgs84(params["south_west_point"][1], params["south_west_point"][0])  # 左下
    # 将许多个点，打包成points。但是一定要注意，点要顺时针
    points = [north_west_point, north_east_point, south_east_point, south_west_point]  # 顺时针
    ring = ogr.Geometry(ogr.wkbLinearRing)  # 环
    polygon = ogr.Geometry(ogr.wkbPolygon)  # 创建面
    for point in points:
        ring.AddPoint(point[0], point[1])  # 经度，纬度
    polygon.AddGeometry(ring)  # 将环加入面
    polygon.CloseRings()  # 首尾关闭
    feat.SetGeometry(polygon)  # 将Geometry给feature
    feat.SetField('name', "用户框选区域")  # 设置字段值
    layer.CreateFeature(feat)  # 并将Feature加入图层

    # 图层范围
    for frame,frame_value in request_points.items():
        ring = ogr.Geometry(ogr.wkbLinearRing)  # 环
        polygon = ogr.Geometry(ogr.wkbPolygon)  # 创建面

        extent_gcj02 = frame_value["extent"]  # [21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]
        if extent_gcj02 is None:
            continue
        y1, x1 = gcj02towgs84(extent_gcj02[1], extent_gcj02[0])
        y2, x2 = gcj02towgs84(extent_gcj02[3], extent_gcj02[2])
        extent_wgs84 = [x1, y1, x2, y2]  # [21.53519080438208, 115.14078044126353, 25.66805217057752, 119.65050502755392]
        for point in [(y1,x1), (y1,x2), (y2,x2), (y2,x1)]:
            ring.AddPoint(point[0], point[1])  # 经度，纬度
        polygon.AddGeometry(ring)  # 将环加入面
        polygon.CloseRings()  # 首尾关闭
        feat.SetGeometry(polygon)  # 将Geometry给feature
        feat.SetField('name', frame)  # 设置字段值
        layer.CreateFeature(feat)  # 并将Feature加入图层

    ds.Destroy()
    return True

def download():
    global data
    global project_dir
    global logger

    logger.info("正在下载数据")

    # original文件夹
    # original_dir = os.path.join(project_dir, "0original")
    # if os.path.exists(original_dir) is False:
    #     os.mkdir(original_dir)
    original_dir = params["original_dir"]


    for frame,frame_value in data.items():
        # 图幅文件夹
        frame_dir = os.path.join(original_dir, frame)
        if os.path.exists(frame_dir) is False:
            os.mkdir(frame_dir)

        for time,time_value in frame_value.items():
            # 已下载-->退出
            if time_value["file_path"] != "":
                continue

            # 下载
            url = time_value["url"]
            fn,fp = download_file(url, frame_dir)
            if fn==None: #下载错误
                logger.error("[下载失败！] {}".format(url) )
                continue #退出
            else: #下载完成
                time_value["file_path"] = fp
                time_value["file_name"] = fn
                # 保存头文件
                hdr_fn = os.path.splitext(fn)[0] #头文件名称
                save_json(frame_dir, hdr_fn, time_value)
                # logger.info("[下载成功] {}".format(fp) )

    logger.info("\t下载数据结束")
    pass


def registration():
    global data
    global data_rgs
    global params
    global logger

    logger.info("正在配准数据")

    rgs_dir = params["registration_dir"]

    for frame,frame_value in data.items():
        for time,time_value in frame_value.items():
            # 原始数据
            origin_file_path = time_value["file_path"] #原始数据文件路径
            if origin_file_path=="":
                # 还没有下载，退出
                continue
            origin_file_name = time_value["file_name"] #原始数据文件名

            # 配准数据
            if frame not in data_rgs:
                data_rgs[frame] = OrderedDict()

            if time in data_rgs[frame]:
                # 该数据已经配准过了
                continue

            # 这个数据还没有配准
            rgs_file_name = "{} {}.tif".format(frame, time) #tif格式
            frame_path = os.path.join(rgs_dir, frame)
            rgs_file_path = os.path.join(frame_path, rgs_file_name)# 配准数据文件路径
            if os.path.exists(rgs_file_path) is True: #配准文件已经存在
                continue

            rgs_data_item = do_rgs(time_value, rgs_file_path)
            if rgs_data_item is None:
                logger.error("[配准失败！] {}".format(origin_file_path) )
            else:
                # 配准完成，保存到data_rgs
                data_rgs[frame][time] = rgs_data_item

    save_json(project_dir, "9 data_rgs", data_rgs) #保存配准信息
    logger.info("\t配准数据结束。")
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
    extent_gcj02 = data_time_value["extent"] #[21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]
    y1, x1 = gcj02towgs84(extent_gcj02[1], extent_gcj02[0])
    y2, x2 = gcj02towgs84(extent_gcj02[3], extent_gcj02[2])
    extent_wgs84 = [x1, y1, x2, y2] #[21.53519080438208, 115.14078044126353, 25.66805217057752, 119.65050502755392]

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
    del ds

    return {
        "extent" : extent_wgs84,
        "file_path" : rgs_file_path
    }


if __name__ == '__main__':
    # start测试
    # params = OrderedDict([('start_time', '2019-03-31 19-46-03'), ('end_time', '\xe6\x9c\xaa\xe8\xae\xbe\xe7\xbd\xae'), ('interval', 5), ('step', 1), ('center_point', (24.696934, 118.083801)), ('south_west_point', (24.319286, 117.641602)), ('north_east_point', (25.072465, 118.526001)), ('south_east_point', (24.319286, 118.526001)), ('north_west_point', (25.072465, 117.641602)), ('save_file_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp'), ('out_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp\\2019-03-31 19-46-03')])
    # req_points = OrderedDict([('0,0', {'req_pnt': (24, 117), 'extent': [21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]}), ('0,1', {'req_pnt': (24, 118), 'extent': [22.41863778627573, 115.8097463696268, 26.550889813724268, 120.35032583037321]})])
    #
    # start(params, req_points)
    #
    # # 【结果】
    # data = OrderedDict([('0,0', OrderedDict([('2019-03-31 17-49-00', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331094900_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554025740.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 17-49-00', 'file_path': ''}), ('2019-03-31 17-54-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331095459_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554026099.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 17-54-59', 'file_path': ''}), ('2019-03-31 18-00-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331100059_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554026459.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-00-59', 'file_path': ''}), ('2019-03-31 18-06-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331100659_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554026819.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-06-59', 'file_path': ''}), ('2019-03-31 18-12-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331101259_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554027179.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-12-59', 'file_path': ''}), ('2019-03-31 18-18-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331101859_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554027539.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-18-59', 'file_path': ''}), ('2019-03-31 18-24-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331102459_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554027899.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-24-59', 'file_path': ''}), ('2019-03-31 18-30-59', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331103059_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554028259.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-30-59', 'file_path': ''}), ('2019-03-31 18-36-58', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331103658_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554028618.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-36-58', 'file_path': ''}), ('2019-03-31 18-42-58', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331104258_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554028978.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-42-58', 'file_path': ''}), ('2019-03-31 18-48-57', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331104857_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554029337.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-48-57', 'file_path': ''}), ('2019-03-31 18-54-57', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331105457_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554029697.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 18-54-57', 'file_path': ''}), ('2019-03-31 19-00-57', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331110057_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554030057.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-00-57', 'file_path': ''}), ('2019-03-31 19-06-57', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331110657_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554030417.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-06-57', 'file_path': ''}), ('2019-03-31 19-12-56', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331111256_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554030776.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-12-56', 'file_path': ''}), ('2019-03-31 19-18-56', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331111856_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554031136.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-18-56', 'file_path': ''}), ('2019-03-31 19-24-55', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331112455_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554031495.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-24-55', 'file_path': ''}), ('2019-03-31 19-30-54', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331113054_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554031854.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-30-54', 'file_path': ''}), ('2019-03-31 19-36-54', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331113654_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554032214.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-36-54', 'file_path': ''}), ('2019-03-31 19-42-54', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331114254_P_DOR_SA_R_10_230_15.596.clean.png', 'timestamp': 1554032574.0, 'req_pnt': (24, 117), 'extent': [21.5327961863, 115.1455902913, 25.6650482137, 119.6549597087], 'time': '2019-03-31 19-42-54', 'file_path': ''})])), ('0,1', OrderedDict([('2019-03-31 17-50-16', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331095016_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554025816.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 17-50-16', 'file_path': ''}), ('2019-03-31 17-55-56', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331095556_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554026156.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 17-55-56', 'file_path': ''}), ('2019-03-31 18-01-37', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331100137_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554026497.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-01-37', 'file_path': ''}), ('2019-03-31 18-07-18', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331100718_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554026838.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-07-18', 'file_path': ''}), ('2019-03-31 18-12-58', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331101258_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554027178.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-12-58', 'file_path': ''}), ('2019-03-31 18-18-40', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331101840_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554027520.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-18-40', 'file_path': ''}), ('2019-03-31 18-24-22', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331102422_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554027862.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-24-22', 'file_path': ''}), ('2019-03-31 18-30-01', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331103001_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554028201.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-30-01', 'file_path': ''}), ('2019-03-31 18-35-43', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331103543_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554028543.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-35-43', 'file_path': ''}), ('2019-03-31 18-41-25', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331104125_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554028885.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-41-25', 'file_path': ''}), ('2019-03-31 18-47-08', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331104708_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554029228.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-47-08', 'file_path': ''}), ('2019-03-31 18-52-48', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331105248_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554029568.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-52-48', 'file_path': ''}), ('2019-03-31 18-58-30', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331105830_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554029910.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 18-58-30', 'file_path': ''}), ('2019-03-31 19-04-11', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331110411_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554030251.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-04-11', 'file_path': ''}), ('2019-03-31 19-09-52', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331110952_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554030592.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-09-52', 'file_path': ''}), ('2019-03-31 19-15-33', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331111533_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554030933.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-15-33', 'file_path': ''}), ('2019-03-31 19-21-15', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331112115_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554031275.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-21-15', 'file_path': ''}), ('2019-03-31 19-26-56', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331112656_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554031616.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-26-56', 'file_path': ''}), ('2019-03-31 19-32-38', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331113238_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554031958.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-32-38', 'file_path': ''}), ('2019-03-31 19-38-20', {'url': u'http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9592_nmc_fast/20190331/Z_RADR_I_Z9592_20190331113820_P_DOR_SA_R_10_230_15.592.clean.png', 'timestamp': 1554032300.0, 'req_pnt': (24, 118), 'extent': [22.4186377863, 115.8097463696, 26.5508898137, 120.3503258304], 'time': '2019-03-31 19-38-20', 'file_path': ''})]))])

    # # extent测试
    # extent_gcj02 = extent_gcj02 = [21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]
    # y1, x1 = gcj02towgs84(extent_gcj02[1], extent_gcj02[0])
    # y2, x2 = gcj02towgs84(extent_gcj02[3], extent_gcj02[2])
    # extent_wgs84 = [x1, y1, x2, y2]
    # print extent_gcj02
    # print extent_wgs84
    #
    # # 配准测试
    # ds = gdal.Open(r"C:\Users\PasserQi\Desktop\testDATA\3,1 2019-04-02 08-56-26.tif", gdal.GA_Update)  # 打开影像
    # # 创建坐标系
    # srs = osr.SpatialReference()
    # srs.SetWellKnownGeogCS('WGS84')
    #
    # rows = ds.RasterYSize #行数
    # cols = ds.RasterXSize #列数
    #
    # # 创建地面控制点：经度、纬度、z，照片列数，照片行数
    # gcps = [
    #     gdal.GCP(y1, x2, 0, 0, 0),  # 左上
    #     gdal.GCP(y2, x2, 0, 0, rows-1),  # 右上
    #     gdal.GCP(y1, x2, 0, cols-1, 0),  # 左下
    #     gdal.GCP(y2, x2, 0, cols-1, rows-1)  # 右下
    # ]
    # ds.SetGCPs(gcps, srs.ExportToWkt())
    # # ds.SetProjection( srs.ExportToWkt() )  # 设置投影
    # # ds.SetGeoTransform(
    # #     gdal.GCPsToGeoTransform(gcps)
    # # )
    # del ds

    # 保存成shp文件出错
    params = OrderedDict([('start_time', '2019-04-02 16-27-59'), ('end_time', '\xe6\x9c\xaa\xe8\xae\xbe\xe7\xbd\xae'), ('interval', 5), ('step', 1), ('center_point', (26.214591, 117.663574)), ('south_west_point', (23.338954, 113.985351)), ('north_east_point', (29.049942, 121.324218)), ('south_east_point', (23.338954, 121.324218)), ('north_west_point', (29.049942, 113.985351)), ('save_file_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp'), ('out_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp\\2019-04-02 16-27-59'), ('remark', u'\u798f\u5efa\u7701'), ('original_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp\\2019-04-02 16-27-59\\0original'), ('registration_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp\\2019-04-02 16-27-59\\1registration_dir'), ('mosaic_dir', 'D:\\mycode\\CrawlerOfPython\\1project\\Precipitation\\tmp\\2019-04-02 16-27-59\\2mosaic_dir')])
    request_points = OrderedDict([('0,0', {'req_pnt': (23, 113), 'extent': [20.93799058627573, 111.11079070210442, 25.070242613724268, 115.60004249789557]}), ('0,2', {'req_pnt': (23, 115), 'extent': [20.75210448627573, 113.1143331315199, 24.884356513724267, 117.5974334684801]}), ('0,4', {'req_pnt': (23, 117), 'extent': [21.21642668627573, 114.49240121633852, 25.34867871372427, 118.99098758366148]}), ('0,5', {'req_pnt': (23, 118), 'extent': [21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]}), ('0,7', {'req_pnt': (23, 120), 'extent': [19.6875, 117.3125, 27.0875, 124.8125]}), ('1,0', {'req_pnt': (24, 113), 'extent': [20.93799058627573, 111.11079070210442, 25.070242613724268, 115.60004249789557]}), ('1,1', {'req_pnt': (24, 114), 'extent': [21.63280168627573, 112.33816630182118, 25.765053713724267, 116.85098369817884]}), ('1,3', {'req_pnt': (24, 116), 'extent': [22.189493386275732, 113.70866955885015, 26.32174541372427, 118.24103044114986]}), ('1,4', {'req_pnt': (24, 117), 'extent': [21.532796186275732, 115.14559029127062, 25.66504821372427, 119.65495970872936]}), ('1,5', {'req_pnt': (24, 118), 'extent': [22.41863778627573, 115.8097463696268, 26.550889813724268, 120.35032583037321]}), ('1,7', {'req_pnt': (24, 120), 'extent': [22.82946008627573, 116.21976121997653, 26.961712113724268, 120.77533318002347]}), ('2,0', {'req_pnt': (25, 113), 'extent': [22.653500333624454, 111.21120725404721, 26.929482866375547, 115.92127034595278]}), ('2,2', {'req_pnt': (25, 115), 'extent': [22.117628133624454, 113.62984589133188, 26.393610666375547, 118.31985410866812]}), ('2,3', {'req_pnt': (25, 116), 'extent': [22.189493386275732, 113.70866955885015, 26.32174541372427, 118.24103044114986]}), ('2,4', {'req_pnt': (25, 117), 'extent': [22.998490586275732, 114.90579501849301, 27.13074261372427, 119.467632581507]}), ('2,5', {'req_pnt': (25, 118), 'extent': [22.82946008627573, 116.21976121997653, 26.961712113724268, 120.77533318002347]}), ('2,7', {'req_pnt': (25, 120), 'extent': [23.92527948627573, 117.2419173304875, 28.057531513724268, 121.83913266951251]}), ('3,0', {'req_pnt': (26, 113), 'extent': [22.653500333624454, 111.21120725404721, 26.929482866375547, 115.92127034595278]}), ('3,2', {'req_pnt': (26, 115), 'extent': [24.52295445620711, 113.46208959720484, 27.235867743792888, 116.47739360279517]}), ('3,3', {'req_pnt': (26, 116), 'extent': [24.942357286275733, 114.76161028798438, 29.07460931372427, 119.39969511201562]}), ('3,4', {'req_pnt': (26, 117), 'extent': [22.998490586275732, 114.90579501849301, 27.13074261372427, 119.467632581507]}), ('3,6', {'req_pnt': (26, 119), 'extent': [23.92527948627573, 117.2419173304875, 28.057531513724268, 121.83913266951251]}), ('4,0', {'req_pnt': (27, 113), 'extent': None}), ('4,1', {'req_pnt': (27, 114), 'extent': None}), ('4,2', {'req_pnt': (27, 115), 'extent': [25.82763508627573, 113.92456271844087, 29.959887113724267, 118.60002608155914]}), ('4,4', {'req_pnt': (27, 117), 'extent': [24.942357286275733, 114.76161028798438, 29.07460931372427, 119.39969511201562]}), ('4,6', {'req_pnt': (27, 119), 'extent': [24.88610728627573, 117.89990515957018, 29.018359313724268, 122.5356724404298]}), ('5,0', {'req_pnt': (28, 113), 'extent': None}), ('5,1', {'req_pnt': (28, 114), 'extent': [26.52279898627573, 113.54843081101693, 30.655051013724268, 118.25446358898309]}), ('5,3', {'req_pnt': (28, 116), 'extent': [25.82763508627573, 113.92456271844087, 29.959887113724267, 118.60002608155914]}), ('5,5', {'req_pnt': (28, 118), 'extent': [26.304872533624454, 115.54592622195182, 30.58085506637555, 120.40890697804818]}), ('5,6', {'req_pnt': (28, 119), 'extent': [26.478343386275732, 117.57540792749619, 30.61059541372427, 122.27945307250381]})])
    project_dir = params["out_dir"]
    save_to_shp()

    pass