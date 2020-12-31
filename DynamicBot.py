from typing                                         import Any
from shutil                                         import rmtree
from bilibili_api                                   import user, Verify
from graia.broadcast                                import Broadcast
from graia.broadcast.entities.event                 import BaseEvent
from graia.broadcast.entities.dispatcher            import BaseDispatcher
from graia.broadcast.interfaces.dispatcher          import DispatcherInterface
from graia.application                              import GraiaMiraiApplication, Session
from graia.application.message.chain                import MessageChain
from graia.application.message.elements.internal    import Plain, Image as ImageQQ
from BasicValues                                    import Values

import threading
import requests
import asyncio
import regex
import time
import yaml
import os

mainLoop = asyncio.get_event_loop()
botBroadcast = Broadcast(loop = mainLoop)
botApp = GraiaMiraiApplication(
    broadcast = botBroadcast,
    enable_chat_log = False,
    connect_info = Session(
        host = Values.HOST.value,
        authKey = Values.AUTH_KEY.value,
        account = Values.BOT_ACCOUNT.value,
        websocket = True
    )
)
with open('BotConfigs.yml', encoding = 'utf-8') as configs:
    configs = yaml.safe_load(configs)
def GetFiles(tarDir, fileName = None):
    dirList = []
    for root, _, files in os.walk(tarDir):
        for filesDir in files:
            if not fileName:
                dirList.append(os.path.join(root, filesDir))
            elif fileName in filesDir:
                dirList.append(os.path.join(root, filesDir))
    return dirList
def ImageDownload(src, des):
    imgData = requests.get(src)
    fileName = f'{des}/{os.path.split(src)[-1]}'
    with open(fileName, 'wb') as pic:
        pic.write(imgData.content)
    return fileName
def RegExMultiPattern(patternList, string):
    return True if [True for pattern in patternList if regex.match(pattern, string)] else False
def GetDynamicInfo(kwDict, keyList):
    def CheckDict(Dict, keys):
        try:
            content = Dict.get(keys[0])
        except:
            return False
        else:
            return CheckDict(content, keys[1:]) if len(keys) > 1 else content
    values = [CheckDict(kwDict, key) for key in keyList]
    return [] if False in values or None in values else values
class BiliDynamicEvent(BaseEvent):
    dynamicInfo: MessageChain
    def __init__(self, dynamicInfo) -> None:
        super().__init__(dynamicInfo = dynamicInfo)
    class Dispatcher(BaseDispatcher):
        def catch(self, interface: DispatcherInterface) -> Any:
            return
def GetLastDynamic(uid, verify):
    while True:
        try:
            dynamic = next(user.get_dynamic_g(uid = uid, verify = verify))
        except Exception as e:
            print(e)
            time.sleep(5)
        else:
            return dynamic
@botBroadcast.receiver(BiliDynamicEvent)
async def SendDynamic(event: BiliDynamicEvent):
    while True:
        try:
            await botApp.sendGroupMessage(Values.MAIN_GROUP.value, event.dynamicInfo)
        except:
            pass
        else:
            break
def MonitorDynamic():
    def EditConfig(dynamicID):
        configs['biliLastDynamicID'] = dynamicID
        with open('BotConfigs.yml', 'w', encoding = 'utf-8') as configFile:
            yaml.safe_dump(configs, configFile, allow_unicode = True, sort_keys = False)
    dynamicInit = GetLastDynamic(Values.BILI_USER_ID.value, BILI_VERIFY)
    dynamicInitID = GetDynamicInfo(dynamicInit, [['desc', 'dynamic_id']])[0]
    EditConfig(dynamicInitID)
    while True:
        while True:
            dynamic = GetLastDynamic(Values.BILI_USER_ID.value, BILI_VERIFY)
            dynamicID = GetDynamicInfo(dynamic, [['desc', 'dynamic_id']])[0]
            if dynamicID != configs['biliLastDynamicID']:
                EditConfig(dynamicID)
                break
            time.sleep(15)
        dynamicInfo = [GetDynamicInfo(dynamic, keys) for keys in BILI_DYNAMIC_KEYS]
        if dynamicInfo[0]:
            if RegExMultiPattern(TEXT_IMAGE_PATTERN, dynamicInfo[0][0]):
                botBroadcast.postEvent(BiliDynamicEvent(MessageChain.create([Plain(dynamicInfo[0][0])] + [ImageQQ.fromLocalFile(ImageDownload(imgInfo['img_src'], BILI_ASSET_PATH)) for imgInfo in dynamicInfo[0][1]])))
        elif dynamicInfo[1]:
            if regex.match('(.|\n)*各位亲爱的指挥官(.|\n)+', dynamicInfo[1][0]):
                botBroadcast.postEvent(BiliDynamicEvent(MessageChain.create([Plain(dynamicInfo[1][0])])))
        elif dynamicInfo[2]:
            botBroadcast.postEvent(BiliDynamicEvent(MessageChain.create([ImageQQ.fromLocalFile(ImageDownload(imgsrc, BILI_ASSET_PATH)) for imgsrc in dynamicInfo[2][0]] + [Plain(f'来自小加加的专栏：\n{dynamicInfo[2][1]}\nhttps://www.bilibili.com/read/cv{dynamicInfo[2][2]}')])))
        elif dynamicInfo[3]:
            botBroadcast.postEvent(BiliDynamicEvent(MessageChain.create([ImageQQ.fromLocalFile(ImageDownload(dynamicInfo[3][0], BILI_ASSET_PATH)), Plain(f'来自小加加的视频：\n{dynamicInfo[3][1]}\nhttps://www.bilibili.com/video/{dynamicInfo[3][2]}')])))
    
BILI_VERIFY = Verify(Values.BILI_SESSDATA.value, Values.BILI_CSRF.value)
CACHE_PATH = './cache'
BILI_ASSET_PATH = f'{CACHE_PATH}/BiliDynamic'
BILI_DYNAMIC_KEYS = [
    [['card', 'item', 'description'], ['card', 'item', 'pictures']],
    [['card', 'item', 'content']],
    [['card', 'image_urls'], ['card', 'title'], ['card', 'id']],
    [['card', 'pic'], ['card', 'title'], ['desc', 'bvid']]
]
TEXT_IMAGE_PATTERN = [
    '#碧蓝航线# \n.+换装(【|「).+(」|】)参上(.|\n)*',
    '#碧蓝航线# \n◆Live2D预览◆(.|\n)*',
    '#碧蓝航线# #舰船新增# (.|\n)+'
]
if not os.path.exists(CACHE_PATH): os.mkdir(CACHE_PATH)
if not os.path.exists(BILI_ASSET_PATH):
    os.mkdir(BILI_ASSET_PATH)
else:
    for files in os.listdir(BILI_ASSET_PATH):
        rmtree(f'{BILI_ASSET_PATH}/{files}', ignore_errors = True)
    for i in GetFiles(BILI_ASSET_PATH):
        os.remove(i)
threading.Thread(target = MonitorDynamic).start()
botApp.launch_blocking()