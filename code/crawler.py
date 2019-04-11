# -*- coding: utf-8 -*-
# @Time    : 2019/4/6 10:30
# @Author  : PasserQi
# @Email   : passerqi@gmail.com
# @File    : crawler
# @Software: PyCharm
# @Version : v1.0.0 2019/3/16
#            v2.0.0 2019/4/6
# @Desc    :

import requests
import json
from collections import OrderedDict
import log
import os

# ===============================================================
#           爬取参数设置
home = "https://api.caiyunapp.com/v1/radar/images"
headers = {
    "User-Agent" : "Dalvik/2.1.0 (Linux; U; Android 8.1.0; MI 5X MIUI/V10.2.3.0.ODBCNXM)",
    "Host" : "api.caiyunapp.com",
    "Connection" : "Keep-Alive",
    "Accept-Encoding" : "gzip"
}
params = {
    # "lon" : lon, # 118.081
    # "lat" : lat, # 24.48176
    "token" : "Y2FpeXVuIGFuZHJpb2QgYXBp",
    "level" : 1,
    "device_id" : "99001113012363"
}

# ============================================================
#           网络模块
def do_get(lat, lon):
    """ 雷达降水图接口
    :param lat: 纬度
    :param lon: 经度
    :return:
        本次请求的images
            [0]: 图片url
            [1]：时间
            [2]：extent gcj02坐标系
        返回失败None
    """
    global home
    global headers
    global params

    params["lon"] = lon
    params["lat"] = lat
    r = requests.get(home, params=params, headers=headers)
    log.getlogger().info("【请求网页】{}".format(r.url))
    json_str = r.text
    ret = json.loads(json_str)
    if "images" not in ret:
        # 该地区没有imgs
        return None
    else:
        imgs = ret["images"]
        if len(imgs)==0 or len(imgs[0])!=3:
            # 出错
            log.getlogger().error("【do_get】imgs出错（可能Url有变）：{}".format(imgs))
            return None
        else:
            return imgs

def get_frames(params):
    """ 得到区域内的图幅
    :param params:
    :return:
    """
    frames = OrderedDict()
    step = params["step"] # 设置步长

    # get four boundary
    extent_gcj02 = params["extent_gcj02"]
    s_boundary, w_boundary,n_boundary, e_boundary = extent_gcj02
    # init processing
    s_boundary = int(s_boundary)
    w_boundary = int(w_boundary)
    n_boundary = int(n_boundary + step/2)
    e_boundary = int(e_boundary + step/2)
    # count the frames
    if abs(n_boundary-s_boundary)<=step and abs(e_boundary-w_boundary)<=step:
        # 小图幅
        center_point = params["points"]["center_point"]
        imgs = do_get(*center_point)
        if imgs!=None:
            frames["0,0"] = {
                "req_pnt" : center_point,
                "extent_gcj02" : imgs[0][2]
            }
        else:
            # 请求不正常
            log.getlogger().error("【get_frames】按用户圈定extent请求，返回的内容不正常！")
            pass
    else:
        # 大图幅
        row = 0
        for x in range(s_boundary, n_boundary, step):
            col = 0
            for y in range(w_boundary, e_boundary, step):
                frame_num = "{},{}".format(row, col)
                imgs = do_get(x, y)
                if imgs!=None:
                    # 图幅正常
                    extent_gcj02 = imgs[0][2]
                else:
                    # 图幅出错
                    extent_gcj02 = None
                frames[frame_num] = {
                    "req_pnt": (x, y),
                    "extent_gcj02": extent_gcj02
                }

                col+=1
            row+=1
        log.save_json("frames-步长{}°".format(step), frames)
        # 根据extent去重，去掉None
        d = frames.copy()
        prior_extent = None
        for key in d:
            value = d[key]
            if prior_extent is None:
                prior_extent = value["extent_gcj02"]
                continue
            else:
                now_extent = value["extent_gcj02"]
                if now_extent is None:
                    frames.pop(key)
                if prior_extent == now_extent:
                    frames.pop(key)
                else:
                    prior_extent = now_extent

    # 计算frames长度
    frame_len = 0
    for key,value in frames.items():
        if value["extent_gcj02"] is not None:
            frame_len +=1
        else:
            continue

    log.save_json("frams", frames)
    return frame_len,frames

def download_file(url, out_dir):
    """ 下载模块
    :param url:
    :param out_dir:
    :return:
    """
    fn = url.split('/')[-1]
    fc = requests.get(url).content
    fp = os.path.join(out_dir, fn)
    with open(fp, "wb") as f:
        f.write(fc)
        return fn, fp
    return None,None