# FFXIVBOT Docker

## 安装Docker

### docker-ce

```bash
curl -sSL https://get.docker.com/ | sh 
```

如果不是root安装，安装过程可能要输入root密码

如果`container.io`的安装有问题，可以通过先`sudo apt-get remove docker-ce`，再`sudo apt-get remove runc`，再重试上述命令尝试解决

### docker-compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

安装后重新登录（或重启shell），然后有两种方式构建项目：

## 1. 自行构建

### 拉取代码

```bash
git clone -b docker https://github.com/Bluefissure/FFXIVBOT.git && cd FFXIVBOT
wget https://github.com/almasaeed2010/AdminLTE/archive/v2.4.5.tar.gz && tar zxf v2.4.5.tar.gz && rm v2.4.5.tar.gz
mv AdminLTE-2.4.5/bower_components static/
mv AdminLTE-2.4.5/dist static/
mv AdminLTE-2.4.5/plugins static/
rm -r AdminLTE-2.4.5/
```

### 环境创建

```bash
docker-compose build --no-cache
```

创建后运行container：

```bash
docker-compose up
```

### 数据同步

```bash
docker-compose run web python manage.py makemigrations
docker-compose run web python manage.py migrate
docker-compose run web python manage.py collectstatic
docker-compose run web python manage.py createsuperuser  #创建管理员
```

访问IP:8000即可访问网页了

## 2. 使用构建好的镜像

```bash
wget https://raw.githubusercontent.com/Bluefissure/FFXIVBOT/docker/release/docker-compose.yml
docker-compose up
```

