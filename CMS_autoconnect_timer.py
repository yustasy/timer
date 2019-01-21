from pprint import pprint
import time
import datetime
import re
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)			# убираем из вывода предупреждение о не достоверных сертификатах

# читаем файл конфигурации

data1 = open('cms.cfg', 'r')
config = {}
for line in data1:
    x = line.split("/")
    a=x[0]
    b=x[1]
    config[a]=b

with open('party.cfg') as data2:
    Party = data2.read().splitlines()

# проверяем время

# преобразуем данные из файла конфигурации в формат date/time

current_time = datetime.datetime.now()
print("Скрипт запущен в ", end='')
print(current_time)

timelist = config['time'].split('.')
datelist = config['date'].split('.')
y = int(datelist[0])
m = int(datelist[1])
d = int(datelist[2])
hr = int(timelist[0])
min = int(timelist[1])
sec = int(timelist[2])
starttime = current_time.replace(year=y, month=m, day=d, hour=hr, minute=min, second=sec, microsecond=0)

# Здесь нужно задать правила подключения

CMS_BASE='https://' + str(config['ip:port'])[:-1] + '/api/v1/'                              # Задаем основные параметры (например IP)
CMS_HEADERS = {'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'authorization': "Basic " + config['base64'][:-1]}    # Задаем логин-пароль (берем из postman)
Domain = "@" + config['userdomain'][:-1]  # это доменная часть - будет прибавляться ко всем номерам (В случае если будет вызов по ip - сделать пустым и писать вместо номеров ip-шники)
Name = str(config['conf_name'][:-1])
URI = str(config['uri'])[:-1]

print('Запланированные дата / время конференции "' + Name + '" ', end='')
print(starttime)

# Autoconnect

def autoconnect(action) :		# Определяем функцию, которую будет удобно вызывать для подключения / отключения всех абонентов списка

    pprint(action)
    global CallID
    if str(action) == "1":     # подключаем абонентов из списка
        for element in Party :
            pprint ("подключаем абонента")
            pprint (element)   #   отслеживаем работу скрипта
            connect = requests.get(CMS_BASE + 'calllegs?filter=' + element, verify=False, headers=CMS_HEADERS)	# проверяем не подключен ли он уже к серверу?
            if ''.join(re.findall(r'callLegs total="(\d)', connect.text)) == '0' :
                requests.post(CMS_BASE + 'calls/' + CallID + '/calllegs', data='remoteParty=' + element + Domain + '&rxAudioMute=true', verify=False, headers=CMS_HEADERS)  # 	операция подключения
            else :
                print("Абонент уже подключен - отмена")
    if str(action) == "2":      # отключаем абонентов из списка
        for element in Party:
            pprint("отключаем абонента")
            pprint (element)
            connect = requests.get(CMS_BASE + 'calllegs?filter=' + element, verify=False, headers=CMS_HEADERS)
            if ''.join(re.findall(r'callLegs total="(\d)', connect.text)) != '0':
                calllegidcurrent = ''.join(re.findall(r'callLeg id="(\w+\-\w+\-\w+\-\w+\-\w+)', connect.text))
                pprint(calllegidcurrent)
                requests.delete(CMS_BASE + 'calllegs/' + calllegidcurrent, verify=False, headers=CMS_HEADERS)
            else :
                print("Абонент не подключен - отмена")

# Проверяем корректность заданной даты / времени

if current_time > (starttime + datetime.timedelta(seconds=60*int(config['duration']) + 5)):
    print("Невозможно планировать конференции в прошедшем времени, конференция должна была закончиться в ", end='')
    print(starttime + datetime.timedelta(seconds=60*int(config['duration'])), end='')
    print(", сейчас ", end='')
    print(current_time)
    exit()

# Запускаем цикл проверки времени

else :
    while datetime.datetime.now() < starttime :
        print('До начала конференции осталось  ', end='')
        print(starttime - datetime.datetime.now())
        time.sleep(5)

coSpaces = requests.get(CMS_BASE + 'coSpaces' + '?filter=' + URI, verify=False, headers=CMS_HEADERS)

if coSpaces.status_code == 200:
    pprint("это то, что выдал request.get:" + coSpaces.text)

SpacesNumber =  int(''.join(re.findall(r'<coSpaces total="(\d+)', coSpaces.text)))
if SpacesNumber == 0:
    print ("Конференция не создана, создаем новую с именем: " + Name)
    coSpace = requests.post(CMS_BASE + 'coSpaces', data=str("name=" + Name + "&uri=" + URI).encode('utf-8'), verify=False, headers=CMS_HEADERS)  # создаем coSpace
    print(coSpace.text)
    coSpaces = requests.get(CMS_BASE + 'coSpaces' + '?filter=' + URI, verify=False, headers=CMS_HEADERS)
    id = ''.join(re.findall(r'<coSpace id="(\w+\-\w+\-\w+\-\w+\-\w+)', coSpaces.text))
    print(id)

elif SpacesNumber == 1:
    id = ''.join(re.findall(r'<coSpace id="(\w+\-\w+\-\w+\-\w+\-\w+)', coSpaces.text))
    print (id)

# Узнаем есть ли открытая медиа сессия

Call = requests.get(CMS_BASE + 'calls' + '?coSpaceFilter=' + id, verify=False, headers=CMS_HEADERS)

if int(''.join(re.findall(r'<calls total="(\d+)', Call.text))) == 0: # Медиа сессии нет - и ее нужно открыть
    pprint ("Нет активной сессии - создаем объект Call")
    response = requests.post(CMS_BASE + 'calls', data= {'coSpace' : id, 'name' : 'autodial', 'allowAllMuteSelf' : 'true', 'allowAllPresentationContribution' : 'true', 'joinAudioMuteOverride' : 'true' }, verify=False, headers=CMS_HEADERS)
    time.sleep(1)
    Call = requests.get(CMS_BASE + 'calls' + '?coSpaceFilter=' + id, verify=False, headers=CMS_HEADERS)
    CallID = ''.join(re.findall(r'<call id="(\w+\-\w+\-\w+\-\w+\-\w+)', Call.text))
else:
    pprint ("Медиа сессия уже существует")
    CallID = ''.join(re.findall(r'<call id="(\w+\-\w+\-\w+\-\w+\-\w+)', Call.text))

pprint ("Это ID медиасессии с которой мы работаем: " + CallID)

autoconnect(1)  # подключаем абонентов

while datetime.datetime.now() < (starttime + datetime.timedelta(seconds=60*(int(config['duration'])-5))):
    print('Конференция запущенна. До конца конференции осталось  ', end='')
    print(starttime + datetime.timedelta(seconds=60*int(config['duration']))- datetime.datetime.now())
    time.sleep(5)

while datetime.datetime.now() < (starttime + datetime.timedelta(seconds=60*(int(config['duration'])))):
    print('Конференция запущенна. До конца конференции осталось менее 5 минут, выводится уведомление о завершении через', end='')
    finishdelta = starttime + datetime.timedelta(seconds=60 * int(config['duration'])) - datetime.datetime.now()
    print(finishdelta)
    requests.put(CMS_BASE + 'calls/' + CallID,data=str('messageText=До завершения конференции осталось ' + str(finishdelta.seconds) + ' секунд' + '&messagePosition=top&messageDuration=1').encode('utf-8'), verify=False, headers=CMS_HEADERS)    # публикация текста
    time.sleep(1)

while datetime.datetime.now() > (starttime + datetime.timedelta(seconds=60 * int(config['duration']))):
    print("конференция завершена")
    autoconnect(2)  # отключаем абонентов
    time.sleep(5)
    quit()



