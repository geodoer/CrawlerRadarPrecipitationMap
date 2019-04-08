# coding:utf8
# @Author:PasserQi
# @Version: v1.0.0 2019/3/16
import requests
import json
from collections import OrderedDict
import os

# debug
from tools import save_json

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

def do_get(lat, lon):
    """ 请求
    :param lat: 纬度
    :param lon: 经度
    :return:
        本次请求的images
            [0]: 图片url
            [1]：时间
            [2]：extent
        返回失败None
    """
    global home
    global headers
    global params

    params["lon"] = lon
    params["lat"] = lat
    r = requests.get(home, params=params, headers=headers)
    print "\t[请求网页]%s" % str(r.url).encode("utf8")
    json_str = r.text
    ret = json.loads(json_str)
    if "images" not in ret: #该地区没有imgs
        return None
    imgs = ret["images"]
    # for image in imgs:
    #     image[1] = timestamp_to_time(image[1]) # 转换时间

    print "\t\t[imgs] %s" % str(imgs)
    return imgs


def init_crawler(params):
    """ 初始化爬取工作
    :param params:
    :return:
    """
    # 图幅的中心点
    request_points = OrderedDict()

    # 四个角坐标
    nepoint = params["north_east_point"]
    # sepoint = params["south_east_point"]
    swpoint = params["south_west_point"]
    # nwpoint = params["north_west_point"]
    # 边界
    s_boundary, w_boundary = swpoint
    n_boundary, e_boundary = nepoint
    s_boundary = int(s_boundary)
    w_boundary = int(w_boundary)
    n_boundary = int(n_boundary + 0.5)
    e_boundary = int(e_boundary + 0.5)
    print s_boundary
    print w_boundary
    print n_boundary
    print e_boundary

    if abs(n_boundary-s_boundary)<=1 and abs(e_boundary-w_boundary)<=1: #小图幅
        center_point = params["center_point"] #取出中心点
        value = {}
        value["req_pnt"] = center_point #请求点

        imgs = do_get(*center_point) #拿中心点请求，看是否正常
        # 如果图幅正常，而且有范围exetent
        if imgs != None and len(imgs) > 0 and len(imgs[0]) >= 3:
            value["extent"] = imgs[0][2]
            request_points["0,0"] = value
        else: #不正常，len(request_points) is 0
            pass
    else: #大图幅
        # 按1°分为一个图幅
        row = 0
        for x in range(s_boundary, n_boundary, 1):
            col = 0
            for y in range(w_boundary, e_boundary, 1):
                sheet_num = str(row) + ',' + str(col)
                value = {}
                value["req_pnt"] = (x,y)
                imgs = do_get(x, y)
                # 如果图幅正常，而且有范围exetent
                if imgs!=None and len(imgs)>0 and len(imgs[0])>=3:
                    value["extent"] = imgs[0][2]
                else:
                    value["extent"] = None
                request_points[sheet_num] = value
                col+=1
            row+=1

        save_path = save_json(params["out_dir"], u"1 request_points - 1度为步长的centerpoint与extent", request_points)
        print u"[FILE] 1度为步长的centerpoint与extent：{}".format(save_path)

        # 根据extent将请求点去重
        prior_extent = None
        for key,value in request_points.items():
            if prior_extent is None:
                prior_extent = value["extent"]
                continue
            else:
                now_extent = value["extent"]
                if prior_extent == now_extent:
                    request_points.pop(key)
                else:
                    prior_extent = now_extent

    # 计算request_point的长度，extent not None才是正常
    img_len = 0
    for key,value in request_points.items():
        if value["extent"] is not None:
            img_len += 1
        else:
            continue


    save_path = save_json(params["out_dir"], u"2 request_points - 每次爬取的中心点坐标", request_points)
    print u"[FILE] 每次爬取的中心点坐标：{}".format(save_path)
    print "【进程】每次需要爬取{}张图片".format( img_len )

    return img_len,request_points

def download_file(url, out_dir):
    fn = url.split('/')[-1]
    fc = requests.get(url).content
    fp = os.path.join(out_dir, fn)
    with open(fp, "wb") as f:
        f.write(fc)
        return fn, fp
    return None,None


if __name__ == '__main__':
    url = "http://cdn.caiyunapp.com/res/storm_radar/radar_NMIC_AZ9596_nmc_fast/20190331/Z_RADR_I_Z9596_20190331094900_P_DOR_SA_R_10_230_15.596.clean.png"
    print download_file(url, r"C:\Users\PasserQi\Desktop")
    pass
