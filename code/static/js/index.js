/*
 @Author:PasserQi
 @Time:2019-4-1
 */
TIME_FORMAT = "yyyy-mm-dd hh-ii";

var map;
$(document).ready(function(){
    var Gaode = L.tileLayer.chinaProvider('GaoDe.Normal.Map', {
        maxZoom: 18,
        minZoom: 5
    });
    map = L.map("map", {
        center: [24.479664, 118.089204],
        zoom: 12,
        layers: [Gaode],
        zoomControl: false,
        doubleClickZoom :false//不可以通过双击放大，因为双击的作用是添加矩形
    });
    L.control.zoom({
        zoomInTitle: '放大',
        zoomOutTitle: '缩小'
    }).addTo(map);

    // 绑定矩形框选择
    $("#rectangleSel").unbind('click').bind('click',function(){
        map.on('mousedown', rectangleMeasure.mousedown).on('mouseup', rectangleMeasure.mouseup);
    });

    // 时间选择器
    $(".form_datetime").datetimepicker({
        language:  'zh-CN',
        format: TIME_FORMAT,
        autoclose: true,
        todayBtn: true,
        minuteStep: 5
    });

    // 拦截表单提交，进行验证
    $("form").submit(checkForm);
});
// leaflet选择矩形框
var rectangleMeasure = {
    startPoint: null,	//起点
    endPoint: null,		//终点
    rectangle : null,		//矩形
    layer: L.layerGroup(),		//图层
    color: "#0D82D7",			//颜色
    ui_ids : ["centerPoint", "leftDwonPoint", "rightUpPoint"],
    appendTarget : "extentSelDiv", //追加HTML的元素
    // 添加矩形
    addRectangle:function(){
        rectangleMeasure.destory(); //销毁原来的矩形
        // 边界
        var bounds = [];
        bounds.push(rectangleMeasure.startPoint);
        bounds.push(rectangleMeasure.endPoint);
        rectangleMeasure.rectangle = L.rectangle(bounds, {color: rectangleMeasure.color, weight: 1}); //创建矩形
        rectangleMeasure.rectangle.addTo(rectangleMeasure.layer); //添加到图层
        rectangleMeasure.layer.addTo(map); //将图层添加到map
    },
    // 添加UI
    addUi:function(){
		// 获得顶点
        var northWestPoint = rectangleMeasure.rectangle.getBounds().getNorthWest(), //左上角
            northEastPoint = rectangleMeasure.rectangle.getBounds().getNorthEast(), //右上角
            southEastPoint = rectangleMeasure.rectangle.getBounds().getSouthEast(), //右下角
            southWestPoint = rectangleMeasure.rectangle.getBounds().getSouthWest(); //左下角
        $("#northWestPoint").val(northWestPoint);
        $("#northEastPoint").val(northEastPoint);
        $("#southEastPoint").val(southEastPoint);
        $("#southWestPoint").val(southWestPoint);
        // 计算中心点
        var centerPoint = rectangleMeasure.rectangle.getCenter();
        $("#centerPoint").val(centerPoint);
        
        // // 计算宽高
        // var width = northWestPoint.distanceTo(northEastPoint)/1000,
        //     height = northEastPoint.distanceTo(southEastPoint)/1000;
        // $("#width").val(width.toFixed(2) + "公里");
        // $("#height").val(height.toFixed(2) + "公里");
        // // 计算面积
        // var area = Number(width) * Number(height);
        // $("#area").val(area.toFixed(2)+"平方公里");
    },
    close:function(){
        rectangleMeasure.destory();
    },
    // 鼠标落下
    mousedown: function(e){
    	rectangleMeasure.destory();
        rectangleMeasure.rectangle = null;
        rectangleMeasure.tips = null;
        map.dragging.disable();
        rectangleMeasure.startPoint = e.latlng;
        map.on('mousemove',rectangleMeasure.mousemove)
    },
    // 鼠标移动
    mousemove:function(e){
        rectangleMeasure.endPoint = e.latlng; //添加终点
        rectangleMeasure.addRectangle(); //添加矩形
        map.off('mousedown ', rectangleMeasure.mousedown).on('mouseup', rectangleMeasure.mouseup);
    },
    // 鼠标落起
    mouseup: function(e){
        map.dragging.enable();
        map.off('mousemove',rectangleMeasure.mousemove).off('mouseup', rectangleMeasure.mouseup).off('mousedown', rectangleMeasure.mousedown);
        rectangleMeasure.addUi();
    },
    // 销毁
    destory:function(){
        if(rectangleMeasure.rectangle)
            rectangleMeasure.layer.removeLayer(rectangleMeasure.rectangle);
		$(".loc").each(function(index, obj){
			$(this).val("正在计算");
		});
    }
};
// 表单检查
function checkForm() {
    // 检查开始时间
    startTime = $("#startTime").val();
    if (startTime=="") {
        $("#errorInfo").html("【错误】开始时间还未选择！");
        return false;
    }
    // 检查矩形
    rectangle = rectangleMeasure.rectangle;
    if (rectangle==null) {
        $("#errorInfo").html("【错误】 爬取范围还未选取！");
        return false;
    }
    // 检查文件夹
    saveDir = $("#saveFileDir").val();
    if (saveDir=="") {
        $("#errorInfo").html("【错误】 保存文件夹还未填写！");
        return false;
    }

    $("#errorInfo").html("表单已提交，后台正在处理。");
    return true;
}