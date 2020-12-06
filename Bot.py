from typing                                         import Any
from pathlib                                        import Path
from BasicValues                                    import Values
from shutil                                         import rmtree
from pixivapi                                       import Client, Size, errors
from graia.broadcast                                import Broadcast
from graia.application                              import GraiaMiraiApplication, Session
from graia.application.message.parser.kanata        import Kanata
from graia.application.message.parser.signature     import RegexMatch, RequireParam, FullMatch
from graia.application.message.chain                import MessageChain
from graia.application.message.elements.internal    import Plain, At, AtAll, Source, Image
from graia.application.group                        import Group, Member
from graia.broadcast.entities.event                 import BaseEvent
from graia.broadcast.entities.dispatcher            import BaseDispatcher
from graia.broadcast.interfaces.dispatcher          import DispatcherInterface
from aiohttp.client_exceptions                      import ClientResponseError
from PixivData                                      import IllustrationSet, ALIllustSet, CopperSet

import datetime as dt
import threading
import asyncio
import random
import regex
import time
import os

mainLoop = asyncio.get_event_loop()
broadcastControl = Broadcast(loop=mainLoop)
botApp = GraiaMiraiApplication(
    broadcast=broadcastControl,
    connect_info=Session(
        host = Values.HOST.value,
        authKey = Values.AUTH_KEY.value,
        account = Values.BOT_ACCOUNT.value,
        websocket = True
    )
)
pixivClient = Client()
pixivClient.login(Values.PIXIV_ACCOUNT.value, Values.PIXIV_PASSWORD.value)
ACCOUNT_ID = Values.PIXIV_ACCOUNT_ID.value
REFRESH_TOKEN = pixivClient.refresh_token
illustQueue = asyncio.Queue(maxsize = 0)
def GetFiles(tarDir, fileName = None):
    dirList = []
    for root, dirs, files in os.walk(tarDir):
        for filesDir in files:
            if not fileName:
                dirList.append(os.path.join(root, filesDir))
            elif fileName in filesDir:
                dirList.append(os.path.join(root, filesDir))
    return dirList
# Dice
class Correction(int):
    def __new__(cls, value):
        value = super().__new__(cls, value)
        value = 1 if value < 1 else value
        return value
@broadcastControl.receiver("GroupMessage", dispatchers = [Kanata([RegexMatch('(.|\n)*(D|d)ice (0*100|0*\d{1,2})d(0*10000|0*\d{1,4})(\+\d+)?$')])])
async def diceHandler(message: MessageChain, bot: GraiaMiraiApplication, group: Group, member: Member):
    DiceSetting = regex.split('(D|d)ice ', message.asDisplay())[-1]
    times, a = DiceSetting.split('d')
    times = int(times)
    faces = a if not '+' in DiceSetting else a.split('+')[0]
    faces = Correction(faces)
    correction = a.split('+')[1] if '+' in DiceSetting else ''
    randomList = []
    for i in range(0, times):
        LocalRandom = random.Random()
        LocalRandom.seed((dt.datetime.now().microsecond << i) + LOWER_SEED + i)
        randomList.append(LocalRandom.randint(1, faces))
    result = sum(randomList)
    if correction != '': randomList.append(int(correction))
    resultWithCorrection = sum(randomList)
    resultList = [DiceSetting]
    if 1 < times <= 4:
        resultList.append(f'{"+".join([str(i) for i in randomList])}')
    elif correction != '':
        resultList.append(f'{result}+{correction}')
    resultList.append(f' {resultWithCorrection}')
    resultStr = '='.join(resultList)
    await bot.sendGroupMessage(group, MessageChain.create([At(member.id), Plain(f' {resultStr}')]), quote = message.get(Source)[0].id)
# Lecture Notice
class UTC(dt.tzinfo):
    def __init__(self, timeZone):
        self._timeZone = timeZone
    def utcoffset(self, _):
        return dt.timedelta(hours = self._timeZone)
    def dst(self, _):
        return dt.timedelta(hours = self._timeZone)
    def tzname(self, _):
        return f'UTC +{self._timeZone}'
class LectureEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        async def catch(self, interface: DispatcherInterface) -> Any:
            return
@broadcastControl.receiver(LectureEvent)
async def LectureNotice():
    #await botApp.sendGroupMessage(Values.MAIN_GROUP.value, MessageChain.create([AtAll(), Plain(f" {'大讲堂' * 3}\n小心欧宅（）")]))
    await botApp.sendGroupMessage(Values.MAIN_GROUP.value, MessageChain.create([Plain(f"{'大讲堂' * 3}\n小心欧宅（）")]))
def LectureTimer(targetTime: dt.time):
    presDatetime = dt.datetime.now(UTC(8))
    dayDiff = 5 - presDatetime.weekday()
    modiDiff = dayDiff if dayDiff >= 0 else 6
    modiDiff = 7 if dayDiff == 0 and (dt.datetime.combine(presDatetime, targetTime) - dt.datetime.combine(presDatetime, presDatetime.time())).days == -1 else modiDiff
    targetDate = presDatetime.date() + dt.timedelta(days = modiDiff)
    targetDatetime = dt.datetime.combine(targetDate, targetTime)
    print(targetDatetime)
    while True:
        while True:
            current = dt.datetime.now(UTC(8))
            if dt.datetime.combine(current.date(), current.time()) >= targetDatetime:
                break
            time.sleep(0.1)
        lectureNoticeEvent = LectureEvent()
        broadcastControl.postEvent(lectureNoticeEvent)
        targetDatetime += dt.timedelta(days = 7)
#illustrations
def PixivRefresh():
    while True:
        time.sleep(1200)
        while True:
            try:
                pixivClient.authenticate(REFRESH_TOKEN)
            except errors.LoginError:
                time.sleep(3)
            else:
                break
        print('Pixiv Client Refreshed.')
def ModifiedGetMethod(func):
    while True:
        try:
            info = func()
        except Exception as e:
            print(e)
            time.sleep(60)
        else:
            break
    return info
async def SendIllust():
    info = await illustQueue.get()
    print(f'Sending {repr(info)}')
    while True:
        try:
            await info[3].sendGroupMessage(info[2], MessageChain.create([Image.fromLocalFile(info[1]), Plain(f'https://www.pixiv.net/artworks/{info[0]}')]))
        except:
            pass
        else:
            break
    return 0
@broadcastControl.receiver('GroupMessage', dispatchers = [Kanata([RegexMatch('^(I|i)llust.*')])])
async def IllustHandler(message: MessageChain, group: Group, bot: GraiaMiraiApplication):
    param = regex.split('(I|i)llust', message.asDisplay())[-1]
    if regex.match('^ (A|a)(L|l)$', param):
        alterSet = ALIllustSet.copy()
        print('Set = AL')
    elif regex.match('^ (C|c)(U|u)$', param):
        alterSet = CopperSet.copy()
        print('Set = Cu')
    else:
        alterSet = IllustrationSet.copy()
        print('Set = Default')
    LocalRandom = random.Random()
    LocalRandom.seed((dt.datetime.now().microsecond << 4) + LOWER_SEED)
    illustID = LocalRandom.choice(tuple(alterSet))
    illust = ModifiedGetMethod(lambda: pixivClient.fetch_illustration(illustID))
    illust.download(directory = Path(IMAGE_PATH), size = Size.ORIGINAL)
    targetIllust = f'{IMAGE_PATH}/{illustID}'
    if os.path.isdir(targetIllust):
        illustImage = LocalRandom.choice(GetFiles(targetIllust))
    else:
        illustImage = GetFiles(IMAGE_PATH, str(illustID))[0]
    await illustQueue.put((illustID, illustImage, group, bot))
    await SendIllust()
LOWER_SEED = random.randint(1, 2 ** 31 - 1)
print(LOWER_SEED)
print(len(IllustrationSet), len(ALIllustSet), len(CopperSet))
CACHE_PATH = './cache'
IMAGE_PATH = f'{CACHE_PATH}/Image'
if not os.path.exists(CACHE_PATH): os.mkdir(CACHE_PATH)
if not os.path.exists(IMAGE_PATH):
    os.mkdir(IMAGE_PATH)
else:
    for files in os.listdir(IMAGE_PATH):
        rmtree(f'{IMAGE_PATH}/{files}', ignore_errors = True)
    for i in GetFiles(IMAGE_PATH):
        os.remove(i)
threading.Thread(target = lambda: LectureTimer(dt.time(11, 30, 00))).start()
threading.Thread(target = lambda: LectureTimer(dt.time(23, 40, 00))).start()
threading.Thread(target = PixivRefresh).start()

botApp.launch_blocking()