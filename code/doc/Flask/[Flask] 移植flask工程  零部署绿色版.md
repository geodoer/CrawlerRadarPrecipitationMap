
【遇到一个项目】
1. 需要用Python爬虫
2. 用户需要有地图进行交互

【传统做法】Tomcat + Python脚本
1. 将Python爬虫的代码打包成exe，方便Java调用
2. 用浏览器做交互，使用ArcGIS api for javascript等地图操作框架
3. 使用Tomcat做服务器，再调用exe实现业务逻辑
例子：https://blog.csdn.net/summer_dew/article/details/80712591
【缺点】难部署；跨语言；或者需要公网IP

【想法一】直接使用Python实现地图交互逻辑，Python地图交互的框架有folium等
1. folium比较冷门，学习周期长

【想法二】用python做服务器，代替传统模式中Tomcat的角色

1. 想到了轻量级的python服务器框架flask，flask很容易使用。
【快速入门】https://blog.csdn.net/summer_dew/article/details/88626849
3. 但是，需要研究如何将工程进行打包成exe（未成功），或者打包成绿色版（成功）

【结果】想法二成功，实现了一个“零部署”的“WebGIS桌面应用”
【优点】易移植；易交互
【缺点】暴露源码；文件大



# 打包成绿色版
> 功能：将开发的文件夹打包成压缩文件-->交付给用户-->解压，点击start.bat即可用！！

【核心】创建一个start.bat文件，在里面写入`python.exe flask入口的py文件`

【例子】
1. 文件夹情况：注意start.bat的位置
![在这里插入图片描述](https://img-blog.csdnimg.cn/20190407093625723.png)
2. python.exe所在目录：在python37/目录下
![在这里插入图片描述](https://img-blog.csdnimg.cn/20190407093724600.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3N1bW1lcl9kZXc=,size_16,color_FFFFFF,t_70)
3. flask代码所在目录：在code/ 目录下![在这里插入图片描述](https://img-blog.csdnimg.cn/20190407093843590.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3N1bW1lcl9kZXc=,size_16,color_FFFFFF,t_70)
4. 编写start.bat文件
```
cd python37
python.exe ..\code\app.py
```


【结果】
![在这里插入图片描述](https://img-blog.csdnimg.cn/20190407094031908.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3N1bW1lcl9kZXc=,size_16,color_FFFFFF,t_70)
【补充】这种情况下，python安装包的两种方法

1. `python.exe -m pip install 包名`
2. 使用pycharm，加入该python.exe，在pycharm软件中安装
# 打包成exe
【做法】使用pyinstaller打包 app.py
【未成功】复杂的工程时，各种报错
【注意】
1. 如果要让flask对应的网页正常打开，需要将templates文件夹复制到dist目录下