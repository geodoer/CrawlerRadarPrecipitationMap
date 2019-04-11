> 本人有JavaWeb基础、Python基础
> 因Python使用爬虫，需要使用flask做前后端交互
> 【选择flask原因】
>   1. 项目需要使用地图进行交互，无奈博主没有接触过Python+地图（开源有folium）
>   2. 使用的是Python爬虫，刚好与flask对接

# 使用前
【巨坑！】一定要设置
【后果】静态文件修改无用
1. 清除浏览器缓存
2. 关闭浏览器缓存

# 创建flask工程
1. pycharm创建工程-->选创建flask工程
2. 选择虚拟环境
3. pycharm帮我们创建了工程目录

# 设置url映射
```python
# 这里url路径和函数名字要一样，博主设成不一样时，有报错
@app.route('/initparam', methods=['post'])
def initparam():
    pass
```

# 引用静态文件
1. 将index.html文件放至templates
2. 将js、css文件放至static
![在这里插入图片描述](https://img-blog.csdnimg.cn/20190317205651709.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3N1bW1lcl9kZXc=,size_16,color_FFFFFF,t_70)
3. Python中设置
```python
app = Flask(__name__,
    static_url_path='' #【注意！】将static路径该为/，文件正常引用
)
@app.route('/')
def index():
    return render_template('index.html') #使用模板index.html
```
4. 静态文件引用
```html
<!-- Leaflet -->
<link href="/js/leaflet/leaflet.css" type="text/css" rel="stylesheet"/>
<script src="/js/leaflet/leaflet.js"></script>
<script src="/js/leaflet/plugins/leaflet.ChineseTmsProviders.js"></script>

<!-- boostrap -->
<link href="/js/bootstrap-3.3.7-dist/css/bootstrap.min.css" rel="stylesheet">
<script src="/js/jquery-3.3.1.js"></script>
<script src="/js/bootstrap-3.3.7-dist/js/bootstrap.min.js"></script>
```


# form
【HTML】写法
```html
// 这里使用了python的url_for()函数，他可以帮我们自动拼接到@app.route('/initparam')的url
<form id='formid' action="{{ url_for('initparam') }}" method="post">
    <button id="rectangleSel" type="button" class="btn btn-default">选取范围</button>
    <!--<input id="centerPoint" name="centerPoint" class="form-control loc" type="text" placeholder="还未选择范围。" readOnly="true">-->
        <!--【ERROR！】 有属性disable，这一行的数据不会被form提交到后端！disable属性会使input无效、也不能被选择！（如果这要不能被修改，使用readOnly，如下）-->
    <input id="centerPoint" name="centerPoint" class="form-control loc" type="text" placeholder="还未选择范围。" readOnly="true">
</form>
```

【flask】
```python
import request # 读form里的参数
@app.route('/initparam', 
    methods=['post'] # 设置methods，表单提交一定要填post
)
def initparam():
    params['center_point'] = request.form.get("centerPoint",  #form中name的值
        type=str #类型
    )
    return 'I get it'
```

# ajax-并将新的HTML显示
【前端】
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
        $('html').html(result); //将后台的html刷新到页面中
        // 对新页面的button进行绑定
        $("#stop").click(function () {
        });
        $("#confirm").click(function () {
        });
    }
});
```
【flask】
```python
@app.route('/dowork', methods=['post'])
def dowork():
    selected_frames_str = request.form.get("selected_frames", type=str)
    frames_selected = json.loads(selected_frames_str)
    
    return render_template('start.html')
```

# 给HTML模板传参数
【Python代码】
```python
@app.route('/dowork', methods=['post'])
def dowork():
    ret = ["你好", "是的！"]
    return render_template('start.html', infos=ret)
```
【HTML页面】对infos循环
```html
<di id="info">
    {% for info in infos %}
        {{ info }}<br/>
    {% endfor %}
</di>
<button id="confirm" type="submit" class="btn btn-default" style="width:100%">开始爬取</button>
<button id="stop" type="submit" class="btn btn-default" style="width:100%">停止爬取</button>
<div id="errorInfo"></div>
```

【对python的dict进行遍历】
```python
{% for frame_num in frames %}
<tr id="{{ frame_num }}">
    <td id="{{ frame_num }}_num">{{ frame_num }}</td>
    <td id="{{ frame_num }}_req_pnt" name="req_pnt">{{ frames[frame_num]["req_pnt"] }}</td>
    <td>
        <input id="{{ frame_num }}_select" type="checkbox" value=""/>
    </td>
</tr>
{% endfor %}
```

# 异步处理后台任务
1. 需要安装futures包
2. 使用多线程（博主使用thread会出错，还未找到原因）

```python
from concurrent.futures import ThreadPoolExecutor #导入包
executor = ThreadPoolExecutor(1) #线程
@app.route('/initparam', methods=['post'])
def initparam():
    params['center_point'] = request.form.get("centerPoint",  #form中name的值
        type=str #类型
    )

    # 开启任务，异步进程
    executor.submit(start(params) ) #异步开启start()函数
    return '已经得到参数，后台正在进行任务'
    
def start(params ):
    print "后台正在处理大任务！"
    pass
```



# 参考文章
1. https://blog.csdn.net/omodao1/article/details/84958172
2. https://www.cnblogs.com/huchong/p/8227606.html
3. 【原理介绍】https://blog.csdn.net/sinat_36651044/article/details/77532510