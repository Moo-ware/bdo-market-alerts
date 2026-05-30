import datetime
import json
import requests
from fuzzywuzzy import fuzz
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


class USEasternTime(datetime.tzinfo):
    standard_offset = datetime.timedelta(hours=-5)
    daylight_offset = datetime.timedelta(hours=1)

    @staticmethod
    def _first_sunday_on_or_after(value):
        days_to_go = 6 - value.weekday()
        if days_to_go:
            value += datetime.timedelta(days=days_to_go)
        return value

    def dst(self, value):
        if value is None:
            return datetime.timedelta(0)

        start = self._first_sunday_on_or_after(datetime.datetime(value.year, 3, 8, 2))
        end = self._first_sunday_on_or_after(datetime.datetime(value.year, 11, 1, 2))
        naive_value = value.replace(tzinfo=None)
        if start <= naive_value < end:
            return self.daylight_offset
        return datetime.timedelta(0)

    def utcoffset(self, value):
        return self.standard_offset + self.dst(value)

    def tzname(self, value):
        return "EDT" if self.dst(value) else "EST"


def get_eastern_timezone():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError:
            pass

    return USEasternTime()


eastern = get_eastern_timezone()
eLevel = {
  0  : "",
  1  : "PRI",
  2  : "DUO",
  3  : "TRI",
  4  : "TET",
  5  : "PEN",
  20 : "PEN",
}

# Subject to change over time
spawnTimes = {
    'Monday' : {
        '0115' : 'Kutum & Karanda',
        '0300' : 'Karanda',
        '0600' : 'Kzarka',
        '1000' : 'Kzarka',
        '1300' : 'Offin',
        '1700' : 'Kutum',
        '2000' : 'Nouver',
        '2315' : 'Kzarka'
    },
    'Tuesday' : {
        '0115' : 'Karanda',
        '0300' : 'Kutum',
        '0600' : 'Kzarka',
        '1000' : 'Nouver',
        '1300' : 'Kutum',
        '1700' : 'Nouver',
        '2000' : 'Karanda',
        '2315' : 'Garmoth'
    },
    'Wednesday' : {
        '0115' : 'Kutum & Kzarka',
        '0300' : 'Karanda',
        '1000' : 'Karanda',
        '1300' : 'Nouver',
        '1700' : 'Kutum & Offin',
        '2000' : 'Vell',
        '2315' : 'Karanda & Kzarka',
        '0015' : 'Quint & Muraka'
    },
    'Thursday' : {
        '0115' : 'Nouver',
        '0300' : 'Kutum',
        '0600' : 'Kzarka',
        '1000' : 'Kutum',
        '1300' : 'Nouver',
        '1700' : 'Kzarka',
        '2000' : 'Kutum',
        '2315' : 'Garmoth'
    },
    'Friday' : {
        '0115' : 'Kzarka & Karanda',
        '0300' : 'Nouver',
        '0600' : 'Karanda',
        '1000' : 'Kutum',
        '1300' : 'Karanda',
        '1700' : 'Nouver',
        '2000' : 'Kzarka',
        '2315' : 'Kutum & Kzarka'
    },
    'Saturday' : {
        '0115' : 'Karanda',
        '0300' : 'Offin',
        '0600' : 'Nouver',
        '1000' : 'Kutum',
        '1300' : 'Nouver',
        '1700' : 'Quint & Muraka',
        '2000' : 'Kzarka & Karanda'
    },
    'Sunday' : {
        '0115' : 'Nouver & Kutum',
        '0300' : 'Kzarka',
        '0600' : 'Kutum',
        '1000' : 'Nouver',
        '1300' : 'Kzarka',
        '1700' : 'Vell',
        '2000' : 'Garmoth',
        '2315' : 'Kzarka & Nouver'
    },
}

dayOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def spawnFromNow():
    spawnList = []
    day = datetime.datetime.now(eastern).strftime('%H%M-%A').split('-')
    for i in spawnTimes[day[1]]:
        if int(noOctal(i)) > int(noOctal(day[0])):
            time = [int(noOctal(i[0:2])) - int(noOctal(day[0][0:2])), int(noOctal(i[2:])) - int(noOctal(day[0][2:]))]
            timefromnow = str(datetime.timedelta(minutes=(time[0] * 60 + time[1] - 1)))[:-3]
            spawnList.append([timefromnow, spawnTimes[day[1]][i]])
        
        elif int(noOctal(i)) == int(noOctal(day[0])) or (int(noOctal(day[0])) - int(noOctal(i))) <= 4 :
            spawnList.append(['SPAWNED', spawnTimes[day[1]][i]])
    
    if len(spawnList) < 3:
        nextDay = day
        if nextDay[1] == 'Sunday':
            nextDay[1] = 'Monday'
        else:
            nextDay[1] = dayOfWeek[dayOfWeek.index(day[1]) + 1]
        for i in spawnTimes[nextDay[1]]:
            time = [int(noOctal(i[0:2])) - int(noOctal(nextDay[0][0:2])), int(noOctal(i[2:])) - int(noOctal(nextDay[0][2:]))]
            timefromnow = str(datetime.timedelta(minutes=(time[0] * 60 + time[1] - 1)))[:-3]
            spawnList.append([timefromnow, spawnTimes[nextDay[1]][i], 1])
        return spawnList
    else:
        return spawnList
  

async def GetWaitlist():
    url = 'https://na-trade.naeu.playblackdesert.com/Home/GetWorldMarketWaitList'
    headers = {
    "Content-Type": "application/json",
    "User-Agent": "BlackDesert"
    }
    payload = {}

    response = requests.request('POST', url, json=payload, headers=headers)
    
    x = json.loads(response.text)
    list = []
    for i in x["_waitList"]: list.append([i['mainKey'], i['name'], i['chooseKey'], i['_waitEndTime'], i['_pricePerOne']])
    return list

async def matchEnhancement(key):
    return eLevel.get(key)


def timeCalc(timestamp):
    td = datetime.datetime.fromtimestamp(timestamp / 1e3) - datetime.datetime.now()
    return int(round(td.total_seconds() / 60))

def noOctal(num):
    for x, i in enumerate(num):
        if int(i) == 0:
            continue  
        return (num[x:])
    return 0


def findNextBoss(boss):
    for i in range(2): # Running the loop 2 times so it can iterate through the dictionary twice
        for day in spawnTimes:
            currentDayVal = dayOfWeek.index(datetime.datetime.now(eastern).strftime('%A'))
            # Only iterate through the whole dictionary on the second loop (i == 1)
            if i == 0:
                if currentDayVal > dayOfWeek.index(day):
                    continue
            # Finding the day and time of next spawn
            for j in spawnTimes[day]:
                if currentDayVal == dayOfWeek.index(day):
                    currentTimeVal = datetime.datetime.now(eastern).strftime('%H%M')
                    if int(noOctal(currentTimeVal)) > int(noOctal(j)):
                        continue
                # See if string is 'something & something'
                if spawnTimes[day][j].find('&') != -1:
                    split = spawnTimes[day][j].split(' & ')
                    for i in split:
                        if i == boss.capitalize():
                            return [day, j]
                if spawnTimes[day][j] == boss.capitalize():
                    return [day, j]


# Time will be a string of format e.g. ['Monday', '0000']
def timeFromNow(timeDay):
    timeNow = datetime.datetime.now(eastern).strftime('%H%M')
    currentDayVal = dayOfWeek.index(datetime.datetime.now(eastern).strftime('%A'))
    # Finding days until timeDay
    if currentDayVal <= dayOfWeek.index(timeDay[0]):
        dayElapsed = dayOfWeek.index(timeDay[0]) - currentDayVal
    else:
        dayElapsed = (dayOfWeek.index(timeDay[0]) + 7) - currentDayVal

    # Finding hours and minutes until timeDay
    timeElapsed = [int(noOctal(timeDay[1][0:2])) - int(noOctal(timeNow[0:2])), int(noOctal(timeDay[1][2:])) - int(noOctal(timeNow[2:]))]
    timefromnow = str(datetime.timedelta(minutes=(timeElapsed[0] * 60 + timeElapsed[1] - 1)))[:-3]

    if timefromnow.find('day') != -1:
        if (dayElapsed - 1) == 0:
            result = 'In {} hr and {} min'.format(timefromnow[8:-3], timefromnow[-2:])
            return result
        else:
            result = 'In {} day {} hr and {} min'.format(dayElapsed - 1, timefromnow[8:-3], timefromnow[-2:])
            return result
    else:
        if dayElapsed == 0:
            result = 'In {} hr and {} min'.format(timefromnow[:-3], timefromnow[-2:])
            return result
        else:    
            result = 'In {} day {} hr and {} min'.format(dayElapsed, timefromnow[:-3], timefromnow[-2:])
            return result
    

def getBossIcon(b):
    if b == 'Gar':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330722239741962/garm.png'
    if b == 'Kza':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330747191656530/Kzarka-modified.png'
    if b == 'Nou':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330770503610540/nouver-modified.png'
    if b == 'Kut':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079329162596188220/Kutum-modified.png'
    if b == 'Kar':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079331502229311598/karan.png'
    if b == 'Off':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330783040393226/Offin-modified.png'
    if b == 'Vel':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330798911619133/Vell-modified.png'
    if b == 'Qui':
        return 'https://cdn.discordapp.com/attachments/629036668531507222/1079330760189812857/Muraka-modified.png'


async def findItems(item, data):
    found_list = []
    for names in data:
        if fuzz.partial_ratio(item.lower(), names[1].lower()) >= 85:
            found_list.append(names)
    
    if len(found_list) > 20 or len(found_list) == 0:
        improved_list=[]
        for names in found_list:
            if fuzz.token_set_ratio(item.lower(), names[1].lower()) >= 90:
                improved_list.append(names)
        return improved_list
    
    return found_list


