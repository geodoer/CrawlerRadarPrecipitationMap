# 时间选择器
【HTML】
```html
<!-- 时间插件 -->
<link href="/js/bootstrap-3.3.7-dist/css/bootstrap-datetimepicker.min.css" rel="stylesheet" />
<script src="/js/bootstrap-3.3.7-dist/js/bootstrap-datetimepicker.min.js"></script>
<script src="/js/bootstrap-3.3.7-dist/js/bootstrap-datetimepicker.zh-CN.js"></script>

<div>
	<label>开始时间</label>
	<div>
	    <input id="startTime" name="startTime" class="form-control" type="text" value="" readonly placeholder="还未选择时间。">
	    <span class="add-on"><i class="icon-remove"></i></span>
	    <span class="add-on"><i class="icon-calendar"></i></span>
	</div>
</div>
```

【Javascript】
```javascript
// 时间选择器
$(".form_datetime").datetimepicker({
    language:  'zh-CN',
    format: TIME_FORMAT,
    autoclose: true,
    todayBtn: true,
    minuteStep: 5
});
```


# 选择器
```javascript
// id选择
$("#submit")
// <tr>
$("tbody > tr").each(function () {
    // 为每个tr绑定事件
    $(this).click(function () {
        var id = $(this).attr("id");
        tr_polygon_click(id);
    });
});
// checkbox点击事件
$("input:checkbox").each(function () {
    $(this).click(function () {
        if (this.checked == true){
            console.log("选择");
        } else {
            console.log("取消选择");
        }
    });
});
// 选择checkbox中已选择
var selected_frames = new Array();
$('input:checkbox:checked').each(function (index, item) {
    selected_frames.push(
        $(this).parents("tr").attr("id");
    );
});
```

# post
```javascript
$.post("/getframesinfo", 
    {},
    function (data) {
        // 将数据加载到图幅中
        console.log(data);
    },
    "json"
);
```

# ajax
```javascript
$.ajax({
    type : "post",
    async : true,
    url : "/dowork",
    data : {
        "selected_frames" : JSON.stringify(selected_frames)
    },
    success: function (result) {
        console.log(result);
    }
});
```

# 表单拦截
```javascript
// 拦截表单提交，进行验证
$("form").submit(checkForm);
// 表单检查
function checkForm() {
	return false; //不提交
    return true;  //提交
}
```