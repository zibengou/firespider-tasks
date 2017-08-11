import asyncio
import aiohttp
import pyodbc
import re
import time
import json
import os
def readFile(path,code="utf-8"):
	if code==None:
		f=open(path,'r')
	else:
		f=open(path,'r',encoding=code)
	res=f.read()
	f.close()
	return res
def writeFile(path,content,wirtetype='w',code='utf-8'):
	if code==None:
		f=open(path,wirtetype)
	else:
		f=open(path,wirtetype,encoding=code)
	f.write(content)
	f.close()
def initConfig(path):
	initJson = json.loads(readFile(path))
	urlObjectList = []
	for jsonObject in initJson:
		for suffix in jsonObject['suffixList']:
			if "~" in suffix:
				startNum = int(regex("(\d.*~)",suffix)[0].replace('~',''))
				endNum = int(regex("(~.*\d)",suffix)[0].replace('~',''))
				for i in range(startNum,endNum+1):
					urlObject = {}
					urlObject['regexList'] = jsonObject['regexList']
					urlObject['group'] = jsonObject['url'].replace("http://",'').replace("www.","").replace(".com","").replace('/','')
					urlObject['url'] = jsonObject['url']+suffix.replace(str(startNum)+"~"+str(endNum),str(i))
					urlObjectList.append(urlObject)
			else:
				urlObject = {}
				urlObject['regexList'] = jsonObject['regexList']
				urlObject['group'] = jsonObject['url'].replace("http://",'').replace("www.","").replace(".com","").replace('/','')
				urlObject['url'] = jsonObject['url'] + suffix
				urlObjectList.append(urlObject)
	return urlObjectList	
				
@asyncio.coroutine
def get_page(url,postdata=None):
	if postdata == None:
		response = yield from aiohttp.request('GET', url)
	else:
		response = yield from aiohttp.request('POST', url,data=postdata)
	return(yield from response.text(encoding='utf-8'))

@asyncio.coroutine
def catchPage(urlObject):
	global resultObject
	try:
		group = resultObject[urlObject['group']]
	except:
		resultObject[urlObject['group']] = []
	reObject={}
	url=urlObject['url']
	sem = asyncio.Semaphore(50)
	with (yield from sem):
		content = yield from get_page(url)
		result = {}
		for regexObject in urlObject['regexList']:
			result[regexObject['name']] = regex(regexObject['regex'],content)
		resultObject[urlObject['group']].append(result)
def regex(pattern,content):
	regex = re.compile(pattern,re.S)
	resultList = re.findall(regex,content)
	return resultList
def run(urlObjectList,fileName):
	global resultObject
	resultObject={}
	loop = asyncio.get_event_loop()
	f = asyncio.wait([catchPage(urlObject) for urlObject in urlObjectList])
	loop.run_until_complete(f)
	filePath ="result/" + str(fileName) + ".json"
	writeFile(filePath,str(resultObject).replace('"',"").replace("'",'"').replace(" ",""))
def execute(path,splitNum):
	urlObjectList = initConfig(path)
	num = len(urlObjectList)%splitNum
	zipped = list(zip(*[iter(urlObjectList)] * splitNum))
	urlObjectListGroup = zipped if not num else zipped + [urlObjectList[-num:],]
	fileName=0
	for i in urlObjectListGroup:
		run(i,fileName)
		fileName+=1
if __name__=='__main__':
	execute("config.json",2)