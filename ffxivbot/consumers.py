from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from channels.layers import get_channel_layer 
from channels.exceptions import StopConsumer
from django.db import transaction
channel_layer = get_channel_layer()
from asgiref.sync import async_to_sync
import json
from collections import OrderedDict
import datetime
import pytz
import re
import os
import pymysql
import time
from ffxivbot.models import *
import ffxivbot.handlers as handlers
from hashlib import md5
import math
import requests
import base64
import random,sys
import traceback  
import codecs
import html
import hmac
import logging
from bs4 import BeautifulSoup
import urllib
import gc
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
CONFIG_PATH = os.environ.get("FFXIVBOT_CONFIG", "/FFXIVBOT/ffxivbot/config.json")

LOGGER = logging.getLogger(__name__)


class WSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            header_list = self.scope["headers"]
            headers = {}
            for (k,v) in header_list:
                headers[k.decode()] = v.decode()
            ws_self_id = headers['x-self-id']
            ws_client_role = headers['x-client-role']
            ws_access_token = headers['authorization'].replace("Token","").strip()
            bot = None
            # with transaction.atomic():
        
            # bot = QQBot.objects.select_for_update().get(user_id=ws_self_id,access_token=ws_access_token)
            bot = QQBot.objects.get(user_id=ws_self_id,access_token=ws_access_token)
        
            self.bot = bot
            self.bot_user_id = self.bot.user_id
            self.bot.event_time = int(time.time())
            self.bot.api_channel_name = self.channel_name
            self.bot.event_channel_name = self.channel_name
            LOGGER.debug("New Universal Connection:%s"%(self.channel_name))
            self.bot.save(update_fields=["event_time","api_channel_name","event_channel_name"])
            LOGGER.debug("Universal Channel connect from {} by channel:{}".format(self.bot.user_id,self.bot.api_channel_name))
            await self.accept()
        except QQBot.DoesNotExist:
            LOGGER.error("%s:%s:API:AUTH_FAIL"%(ws_self_id, ws_access_token))
            await self.close()
            return
        except Exception as e:
            traceback.print_exc()
            await self.close()
            return
        
    async def disconnect(self, close_code):
        try:
            self.pub.exit()
            LOGGER.debug("Universal Channel disconnect from {} by channel:{} {}s".format(
                self.bot.user_id,
                self.channel_name,
                int(time.time())-int(self.bot.api_time)))
            gc.collect()
        except:
            pass
        raise StopConsumer

    async def receive(self, text_data):
        # try:
        #     # self.bot = QQBot.objects.select_for_update().get(user_id = self.bot_user_id)
        #     self.bot = QQBot.objects.get(user_id = self.bot_user_id)
        # except QQBot.DoesNotExist:
        #     LOGGER.error("QQBot.DoesNotExist:{}".format(self.bot_user_id))
        #     return
        receive = json.loads(text_data)
        # print("receiving data:{}\n============================".format(json.dumps(receive)))
        
        if "post_type" in receive.keys():
            self.bot.event_time = int(time.time())
            self.bot.save(update_fields=["event_time"])
            self.config = json.load(open(CONFIG_PATH,encoding="utf-8"))
            for (k, v) in self.config.items():
                self.config[k] = os.environ.get(k, v)
            already_reply = False
            try:
                receive = json.loads(text_data)
                if(receive["post_type"] == "meta_event" and receive["meta_event_type"] == "heartbeat"):
                    LOGGER.info("bot:{} Event heartbeat at time:{}".format(self.bot.user_id, int(time.time())))
                    # await self.call_api("get_status",{},"get_status:{}".format(self.bot_user_id))
                try:
                    self_id = receive["self_id"]
                    try:
                        bot = QQBot.objects.get(user_id=self_id)
                    except QQBot.DoesNotExist as e:
                        LOGGER.error("bot {} does not exsit.".format(self_id))
                        raise e
                    config = self.config
                    already_reply = False

                    if(receive["post_type"] == "meta_event" and receive["meta_event_type"] == "heartbeat"):
                        LOGGER.debug("bot:{} Event heartbeat at time:{}".format(self_id, int(time.time())))
                        await self.call_api(bot, "get_status",{},"get_status:{}".format(self_id))

                    if (receive["post_type"] == "message"):
                        # LOGGER.info('%s Handling message %s', os.getpid(), receive["message"])
                        # Self-ban in group
                        user_id = receive["user_id"]
                        if(QQBot.objects.filter(user_id=user_id).count()>0):
                            raise Exception("{} reply from another bot:{}".format(receive["self_id"], user_id))
                            # LOGGER.error("{} reply from another bot:{}".format(receive["self_id"], user_id))
                            # self.acknowledge_message(basic_deliver.delivery_tag)
                            # return

                        for (alter_command, command) in handlers.alter_commands.items():
                            if(receive["message"].find(alter_command)==0):
                                receive["message"] = receive["message"].replace(alter_command, command, 1)
                                
                        group_id = None
                        group = None
                        group_created = False
                        #Group Control Func
                        receive["message"] = receive["message"].replace('\\', '/', 1)
                        if (receive["message_type"]=="group"):
                            group_id = receive["group_id"]
                            (group, group_created) = QQGroup.objects.get_or_create(group_id=group_id)
                            if(int(time.time()) < group.ban_till):
                                raise Exception("{} banned by group:{}".format(self_id, group_id))
                                # LOGGER.info("{} banned by group:{}".format(self_id, group_id))
                                # self.acknowledge_message(basic_deliver.delivery_tag)
                                # return
                            group_commands = json.loads(group.commands)

                            try:
                                member_list = json.loads(group.member_list)
                                if group_created or not member_list:
                                    await self.update_group_member_list(bot, group_id)
                            except:
                                member_list = []
                                
                            
                            if (receive["message"].find('/group_help')==0):
                                msg =  "" if member_list else "本群成员信息获取失败，请尝试重启酷Q并使用/update_group刷新群成员信息"
                                for (k, v) in handlers.group_commands.items():
                                    msg += "{} : {}\n".format(k,v)
                                msg = msg.strip()
                                await self.send_message(bot, receive["message_type"], group_id or user_id, msg)
                            else:
                                if(receive["message"].find('/update_group')==0):
                                    await self.update_group_member_list(bot, group_id)
                                #get sender's user_info

                                user_info = receive["sender"] if "sender" in receive.keys() else None
                                user_info = user_info if user_info and "role" in user_info.keys() else None
                                if member_list and not user_info:
                                    for item in member_list:
                                        if(int(item["user_id"])==int(user_id)):
                                            user_info = item
                                            break
                                if not user_info:
                                    raise Exception("No user info for user_id:{} in group:{}".format(user_id, group_id))

                                group_command_keys = sorted(handlers.group_commands.keys())
                                group_command_keys.reverse()
                                for command_key in group_command_keys:
                                    if(receive["message"].find(command_key)==0):
                                        if receive["message_type"]=="group" and group_commands:
                                            if command_key in group_commands.keys() and group_commands[command_key]=="disable":
                                                continue
                                        if not group.registered and command_key!="/group":
                                            msg = "本群%s未在数据库注册，请群主使用/register_group命令注册"%(group_id)
                                            await self.send_message(bot, "group", group_id, msg)
                                            break
                                        else:
                                            handle_method = getattr(handlers,"QQGroupCommand_{}".format(command_key.replace("/","",1)))
                                            action_list = handle_method(receive = receive, 
                                                                        global_config = config, 
                                                                        bot = bot, 
                                                                        user_info = user_info, 
                                                                        member_list = member_list, 
                                                                        group = group,
                                                                        commands = handlers.commands,
                                                                        group_commands = handlers.group_commands,
                                                                        alter_commands = handlers.alter_commands,
                                                                        )
                                            for action in action_list:
                                                await self.call_api(bot, action["action"],action["params"],echo=action["echo"])
                                            already_reply = True
                                            break

                            if not already_reply:
                                action_list = handlers.QQGroupChat(receive = receive, 
                                                                    global_config = config, 
                                                                    bot = bot, 
                                                                    user_info = user_info, 
                                                                    member_list = member_list, 
                                                                    group = group,
                                                                    commands = handlers.commands,
                                                                    alter_commands = handlers.alter_commands,
                                                                    )
                                for action in action_list:
                                    await self.call_api(bot, action["action"],action["params"],echo=action["echo"])
                    



                        
                        

                        if (receive["message"].find('/help')==0):
                            msg =  ""
                            for (k, v) in handlers.commands.items():
                                msg += "{} : {}\n".format(k,v)
                            msg += "具体介绍详见Wiki使用手册: {}\n".format("https://github.com/Bluefissure/FFXIVBOT/wiki/")
                            msg = msg.strip()
                            await self.send_message(bot, receive["message_type"], group_id or user_id, msg)

                        if (receive["message"].find('/ping')==0):
                            msg =  ""
                            if "detail" in receive["message"]:
                                msg += "[CQ:at,qq={}]\ncoolq->server: {:.2f}s\nserver->rabbitmq: {:.2f}s".format(
                                    receive["user_id"], 
                                    receive["consumer_time"]-receive["time"], 
                                    time.time()-receive["consumer_time"])
                            else:
                                msg += "[CQ:at,qq={}] {:.2f}s".format(receive["user_id"], time.time()-receive["time"])
                            msg = msg.strip()
                            LOGGER.debug("{} calling command: {}".format(user_id, "/ping"))
                            await self.send_message(bot, receive["message_type"], group_id or user_id, msg)

                        

                        command_keys = sorted(handlers.commands.keys())
                        command_keys.reverse()
                        for command_key in command_keys:
                            if(receive["message"].find(command_key)==0):
                                if receive["message_type"]=="group" and group_commands:
                                    if command_key in group_commands.keys() and group_commands[command_key]=="disable":
                                        continue
                                LOGGER.debug("{} calling command: {}".format(user_id, command_key))
                                handle_method = getattr(handlers,"QQCommand_{}".format(command_key.replace("/","",1)))
                                action_list = handle_method(receive=receive, global_config=config, bot=bot)
                                # if(len(json.loads(bot.disconnections))>100):
                                #     action_list = self.intercept_action(action_list)
                                for action in action_list:
                                    await self.call_api(bot, action["action"],action["params"],echo=action["echo"])
                                    already_reply = True
                                break

                        
                    CONFIG_GROUP_ID = config["CONFIG_GROUP_ID"]
                    if (receive["post_type"] == "request"):
                        if (receive["request_type"] == "friend"):   #Add Friend
                            qq = receive["user_id"]
                            flag = receive["flag"]
                            if(bot.auto_accept_friend):
                                reply_data = {"flag":flag, "approve": True}
                                await self.call_api(bot, "set_friend_add_request",reply_data)
                        if (receive["request_type"] == "group" and receive["sub_type"] == "invite"):    #Invite Group
                            flag = receive["flag"]
                            if(bot.auto_accept_invite):
                                reply_data = {"flag":flag, "sub_type":"invite", "approve": True}
                                await self.call_api(bot, "set_group_add_request",reply_data)
                        if (receive["request_type"] == "group" and receive["sub_type"] == "add" and str(receive["group_id"])==CONFIG_GROUP_ID):    #Add Group
                            flag = receive["flag"]
                            user_id = receive["user_id"]
                            qs = QQBot.objects.filter(owner_id=user_id)
                            if(qs.count()>0):
                                reply_data = {"flag":flag, "sub_type":"add", "approve": True}
                                await self.call_api(bot, "set_group_add_request",reply_data)
                                reply_data = {"group_id":CONFIG_GROUP_ID, "user_id":user_id, "special_title":"饲养员"}
                                await self.call_api(bot, "set_group_special_title", reply_data)
                    if (receive["post_type"] == "event"):
                        if (receive["event"] == "group_increase"):
                            group_id = receive["group_id"]
                            user_id = receive["user_id"]
                            try:
                                group = QQGroup.objects.get(group_id=group_id)
                                msg = group.welcome_msg.strip()
                                if(msg!=""):
                                    msg = "[CQ:at,qq=%s]"%(user_id)+msg
                                    await self.send_message(bot, "group", group_id, msg)
                            except:
                                traceback.print_exc()
                    # print(" [x] Received %r" % body)
                except Exception as e:
                    LOGGER.error(e)
                except:
                    traceback.print_exc()



            except Exception as e:
                traceback.print_exc() 
            # self.bot.save()
        else:
            self.bot.api_time = int(time.time())
            self.bot.save(update_fields=["api_time"])
            if(int(receive["retcode"])!=0):
                if (int(receive["retcode"])==1 and receive["status"]=="async"):
                    LOGGER.warning("API waring:"+text_data)
                else:
                    LOGGER.error("API error:"+text_data)
            if("echo" in receive.keys()):
                echo = receive["echo"]
                LOGGER.debug("echo:{} received".format(receive["echo"]))
                if(echo.find("get_group_member_list")==0):
                    group_id = echo.replace("get_group_member_list:","").strip()
                    try:
                        # group = QQGroup.objects.select_for_update().get(group_id=group_id)
                        group = QQGroup.objects.get(group_id=group_id)
                        member_list = json.dumps(receive["data"]) if receive["data"] else "[]"
                        group.member_list = member_list
                        group.save(update_fields=["member_list"])
                        #await self.send_message("group", group_id, "群成员信息刷新成功")
                    except QQGroup.DoesNotExist:
                        LOGGER.error("QQGroup.DoesNotExist:{}".format(self.group_id))
                        return
                    LOGGER.debug("group %s member updated"%(group.group_id))
                if(echo.find("get_group_list")==0):
                    self.bot.group_list = json.dumps(receive["data"])
                    self.bot.save(update_fields=["group_list"])
                if(echo.find("_get_friend_list")==0):
                    # friend_list = echo.replace("_get_friend_list:","").strip()
                    self.bot.friend_list = json.dumps(receive["data"])
                    self.bot.save(update_fields=["friend_list"])
                if(echo.find("get_version_info")==0):
                    self.bot.version_info = json.dumps(receive["data"])
                    self.bot.save(update_fields=["version_info"])
                if(echo.find("get_status")==0):
                    user_id = echo.split(":")[1]
                    if(not receive["data"] or not receive["data"]["good"]):
                        LOGGER.error("bot:{} not good at time:{}".format(user_id, int(time.time())))
                    else:
                        LOGGER.debug("bot:{} Universal heartbeat at time:{}".format(user_id, int(time.time())))
            # self.bot.save()



    async def send_event(self, event):
        LOGGER.debug("Universal Channel {} send_event with event:{}".format(self.channel_name, json.dumps(event)))
        
        # print("sending event:{}\n============================".format(json.dumps(event)))
        await self.send(event["text"])

    async def call_api(self, action, params, echo=None):
        # print("calling api:{} {}\n============================".format(json.dumps(action),json.dumps(params)))
        if("async" not in action and not echo):
            action = action + "_async"
        jdata = {
            "action":action,
            "params":params,
        }
        if echo:
            jdata["echo"] = echo
        await self.send_event({"type": "send.event","text": json.dumps(jdata),})

    async def send_message(self, private_group, uid, message):
        if(private_group=="group"):
           await self.call_api("send_group_msg",{"group_id":uid,"message":message})
        if(private_group=="private"):
           await self.call_api("send_private_msg",{"user_id":uid,"message":message})



    async def update_group_member_list(self,group_id):
        await self.call_api("get_group_member_list",{"group_id":group_id},"get_group_member_list:%s"%(group_id))

    async def delete_message(self, message_id):
        await self.call_api("delete_msg",{"message_id":message_id})


    async def group_ban(self,group_id,user_id,duration):
        json_data = {"group_id":group_id,"user_id":user_id,"duration":duration}
        await self.call_api("set_group_ban",json_data)

    def intercept_action(self, action_list):
        modified_action_list = action_list
        for i in range(len(modified_action_list)):
            if "message" in modified_action_list[i]["params"].keys():
                modified_action_list[i]["params"]["message"] = "此獭獭由于多次重连已被暂时停用，请联系开发者恢复，"
        return modified_action_list
