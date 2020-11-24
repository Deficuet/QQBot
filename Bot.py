from typing                                         import Any
from BasicValues                                    import Values
from graia.broadcast                                import Broadcast
from graia.application                              import GraiaMiraiApplication, Session
from graia.application.message.parser.kanata        import Kanata
from graia.application.message.parser.signature     import RegexMatch, RequireParam, FullMatch
from graia.application.message.chain                import MessageChain
from graia.application.message.elements.internal    import Plain, At, Source
from graia.application.group                        import Group, Member
from graia.broadcast.entities.event                 import BaseEvent
from graia.broadcast.entities.dispatcher            import BaseDispatcher
from graia.broadcast.interfaces.dispatcher          import DispatcherInterface

import datetime as dt
import threading
import asyncio
import random
import time

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
# Dice
@broadcastControl.receiver("GroupMessage", dispatchers = [Kanata([RegexMatch('(.|\n)*Dice (0*100|0*\d{1,2})d(0*10000|0*[1-9](\d{1,3})?)(\+\d+)?$')])])
async def diceHandler(message: MessageChain, bot: GraiaMiraiApplication, group: Group, member: Member):
    DiceSetting = message.asDisplay().split('Dice ')[-1]
    times, a = DiceSetting.split('d')
    times = int(times)
    faces = a if not '+' in DiceSetting else a.split('+')[0]
    faces = int(faces)
    correction = a.split('+')[1] if '+' in DiceSetting else ''
    randomList = []
    for _ in range(0, times):
        randomList.append(random.randint(1, faces))
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
    await botApp.sendGroupMessage(Values.MAIN_GROUP.value, MessageChain.create([Plain('大讲堂' * 3)]))
def LectureTimer(targetTime: dt.time):
    presDatetime = dt.datetime.now(UTC(8))
    dayDiff = 5 - presDatetime.weekday()
    modiDiff = dayDiff if dayDiff >= 0 else 6
    modiDiff = 7 if dayDiff == 0 and (dt.datetime.combine(presDatetime, targetTime) - presDatetime).days == -1 else modiDiff
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
threading.Thread(target = lambda: LectureTimer(dt.time(11, 30, 00))).start()
threading.Thread(target = lambda: LectureTimer(dt.time(23, 40, 00))).start()

botApp.launch_blocking()