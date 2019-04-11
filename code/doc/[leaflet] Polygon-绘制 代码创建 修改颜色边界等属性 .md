【参考文章记录】
2. leaflet加载高德地图：https://blog.csdn.net/GISuuser/article/details/77600052
3. leaflet加载点、线、面：https://blog.csdn.net/lonly_maple/article/details/83545997

# 依赖包
```HTML
<!-- Leaflet -->
<link href="/js/leaflet/leaflet.css" type="text/css" rel="stylesheet"/>
<script src="/js/leaflet/leaflet.js"></script>
<script src="/js/leaflet/plugins/leaflet.ChineseTmsProviders.js"></script>

<!-- boostrap -->
<link href="/js/bootstrap-3.3.7-dist/css/bootstrap.min.css" rel="stylesheet">
<script src="/js/jquery-3.3.1.js"></script>
<script src="/js/bootstrap-3.3.7-dist/js/bootstrap.min.js"></script>
```

# 绘制面
```javascript
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
```


# 代码创建面
## 创建底图
```javascript
var map;
$(document).ready(function(){
    var Gaode = L.tileLayer.chinaProvider('GaoDe.Normal.Map', {
        maxZoom: 18,
        minZoom: 5
    });
    map = L.map("map", {
        center: [24.479664, 118.089204],
        zoom: 1,
        layers: [Gaode],
        zoomControl: false,
        doubleClickZoom :false//不可以通过双击放大，因为双击的作用是添加矩形
    });
    L.control.zoom({
        zoomInTitle: '放大',
        zoomOutTitle: '缩小'
    }).addTo(map);
});
```
## 创建面
```javascript
// 全局变量
var polygonGroup;  //图层：用来存放polygon
var polygons = []; //面状数据：管理polygon
// 创建图层，用来存放polygon
polygonGroup = new L.featureGroup([]);
map.addLayer(polygonGroup);
// 创建面
add_poylgon("extent_gcj02", "用户框选的位置", result["extent_gcj02"]);
function add_poylgon(id, name, extent) {
    // params: id str 面状地物的id
    // params: name str 面状地图的名字
    // params: extent [] 矩阵的范围
    var x1 = extent[0];
    var y1 = extent[1];
    var x2 = extent[2];
    var y2 = extent[3];

    // 渲染
    var color = "#1F78FF";
    var fillColor = '#38CCFF';
    var fillOpacity = 0;
    // 矩阵
    var polygon = L.polygon([ //闭合的点数据
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
        [x1, y1]
    ], { //设置渲染
        color : color,
        fillColor : fillColor,
        fillOpacity : fillOpacity
    }).addTo(polygonGroup); //加载到polygonGroup
    // 设置属性
    polygon["attr"] = {
        "name" : name,
        "id" : id
    };
    // 点击事件
    polygon.on('click', function (e) {
        console.log(e);
        var target = e["target"];
        var attr = target["attr"];
        var id = attr["id"];
        tr_polygon_click(id); //polygon被点击
    });
    // 弹出框
    polygon.bindPopup(name);
    // 添加到集合中
    polygons[id] = polygon;
}
```
## 修改面的属性：颜色、透明度等
```javascript
function alter_attr(id, attrname, attrvalue) {
    var polygon = polygons[id];
    polygonGroup.removeLayer(polygon); //移除
    // 修改属性
    polygon["options"][attrname] = attrvalue;
    polygonGroup.addLayer(polygon); // 添加
}
```

## 事件
```javascript
// 创建点击事件
polygon.on('click', function (e) {
    console.log(e);
    var target = e["target"];
    var attr = target["attr"];
    var id = attr["id"];
    tr_polygon_click(id);
});
//手动触发polygon的点击事件
polygons[id].fire("click"); 
```

## 地图与表格联动
【效果展示】


```javascript
function init_binding() {
    // 表格被点击
    $("tbody > tr").each(function () {
        // 为每个tr绑定事件
        $(this).click(function () {
            var id = $(this).attr("id");
            tr_polygon_click(id);
        });
    });
    // 面的点击事件
    polygon.on('click', function (e) {
        console.log(e);
        var target = e["target"];
        var attr = target["attr"];
        var id = attr["id"];
        tr_polygon_click(id); //polygon被点击
    });
}

// 点击时的响应事件
var lastClickPolygonId;
function tr_polygon_click(id) {
    // tr响应
    $("tbody tr").each(function () {
        $(this).removeClass();
    });
    $("tr[id='" + id + "']").attr("class", "info");
    // polygon响应：变绿色
    if (lastClickPolygonId!=null) { //上一个变回来
        alter_attr(lastClickPolygonId, "color","#1F78FF")
    }
    lastClickPolygonId = id;
    alter_attr(id, "color","#00FF00")
}
```
