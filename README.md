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

将如下内容保存为`docker-compose.yml`

```yml
version: '3'

services:
  db:
    image: mysql:5.6
    container_name : ffxivbot-db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: FFXIV_DEV
    volumes:
      - ./docker/mysql-data:/var/lib/mysql
    networks:
      - ffxivbot_network
  web:
    container_name : ffxivbot-web
    image: 'bluefissure/ffxivbot:latest'
    depends_on:
      - db
      - redis
    networks:
      - ffxivbot_network
    ports:
      - 8000:8002
    restart: on-failure
    command: daphne FFXIVBOT.asgi:application -b 0.0.0.0 -p 8002
  redis:
    container_name : ffxivbot-redis
    image: "redis:alpine"
    networks:
      - ffxivbot_network
networks:
  ffxivbot_network:
volumes:
  mysql-data:
```

然后直接`docker-compose up`
