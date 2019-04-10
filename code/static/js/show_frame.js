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

    add_frames(); //添加图幅到map上
});
//<td class="success">...</td> info

// https://blog.csdn.net/lonly_maple/article/details/83545997
var polygonGroup; //polygon图层
var polygons = {}; //保存每一个polygon
function add_frames() {
    $("#errorInfo").html("正在加载图幅，请稍后。");
    $.post("/getframesinfo", {},
        function (data) {
            // 将数据加载到图幅中
            console.log(data);
            var result = data["result"];
            // 创建图层
            polygonGroup = new L.featureGroup([]);
            map.addLayer(polygonGroup);
            // 图幅
            var frames = result["frames"];
            $.each(frames, function (key, value) {
                add_poylgon(key, "图幅号"+key, value["extent_gcj02"]); //添加矩阵
            });
            $("#errorInfo").html("红色边框：上一步所框选区域。蓝色矩形：已选择");
            // 用户框选的位置
            add_poylgon("extent_gcj02", "用户框选的位置", result["extent_gcj02"]);

            init_binding(); //初始化绑定
        },
        "json"
    );
}

function add_poylgon(id, name, extent) {
    var x1 = extent[0];
    var y1 = extent[1];
    var x2 = extent[2];
    var y2 = extent[3];

    // 色彩
    var color, fillColor, fillOpacity;
    if (id=="extent_gcj02") { //用户选择的区域
        color = '#FF0000';
        fillColor = '#FFCDCA';
        fillOpacity = 0;
    } else { //图幅
        color = "#1F78FF";
        fillColor = '#38CCFF';
        fillOpacity = 0;
    }
    // 矩阵
    var polygon = L.polygon([
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
        [x1, y1]
    ], {
        color : color,
        fillColor : fillColor,
        fillOpacity : fillOpacity
    }).addTo(polygonGroup);
    if (id=="extent_gcj02") {
        return ;
    }
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
        tr_polygon_click(id);
    });
    // 弹出框
    polygon.bindPopup(name);
    // 添加到集合中
    polygons[id] = polygon;
}

// 事件绑定
var lastPnt = null;
function init_binding() {
    //提交选择
    $("#submit").click(dowork);
    // <tr>被点击
    $("tbody > tr").each(function () {
        // 为每个tr绑定事件
        $(this).click(function () {
            var id = $(this).attr("id");
            tr_polygon_click(id);
        });
    });
    // <checkbox>被点击
    $("input:checkbox").each(function () {
        $(this).click(function () {
            var id = $(this).parents("tr").attr("id");
            console.log(id);
            if (this.checked == true){
                console.log("选择");
                alter_attr(id, "fillOpacity", 0.5)
            } else {
                console.log("取消选择");
                alter_attr(id, "fillOpacity", 0)
            }
        });
    });
    // req_pnt被点击
    $("td[name='req_pnt']").each(function () {
        $(this).click(function () {
            if (lastPnt!=null) {
                polygonGroup.removeLayer(lastPnt);
            }
            str = $(this).text();
            console.log(str);
            XY = str.replace('(', '').replace(')', '').split(',');
            x = parseFloat(XY[0]);
            y = parseFloat(XY[1]);
            lastPnt = L.marker([x, y]).bindPopup("该图幅的请求点" + str).addTo(polygonGroup);
            lastPnt.fire("click");
        });
    });
}

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

function alter_attr(id, attrname, attrvalue) {
    var polygon = polygons[id];
    polygonGroup.removeLayer(polygon); //移除
    // 修改属性
    polygon["options"][attrname] = attrvalue;
    polygonGroup.addLayer(polygon); // 添加
}

function dowork() { //提交选择的图幅
    // 获取选中的值
    var selected_frames = new Array();
    $('input:checkbox:checked').each(function (index, item) {
        selected_frames.push(
            $(this).parents("tr").attr("id")
        );
    });
    console.log(selected_frames);
    if (selected_frames.length==0) {
        $("#errorInfo").html("还未选择图幅");
        return ;
    }
    $("#errorInfo").html("正在爬取，可关闭此网页。");
    $.ajax({
        type : "post",
        async : true,
        url : "/dowork",
        data : {
            "selected_frames" : JSON.stringify(selected_frames)
        },
        success: function (result) {
            console.log(result);
            $('html').html(result);
            $("#stop").click(function () {
                $.ajax({
                    type : "post",
                    async : true,
                    url : "/stop",
                    data : {},
                    success: function (result) {
                        $("#errorInfo").html(result);
                    }
                })
            });
            $("#confirm").click(function () {
                $.ajax({
                    type : "post",
                    async : true,
                    url : "/start",
                    data : {},
                    success: function (result) {
                        $("#errorInfo").html(result);
                    }
                });
                $("#errorInfo").html("正在爬取，可关闭此网页。");
            });
        }
    });
}