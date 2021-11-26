import requests

from pyquery import PyQuery
import logging
logging.captureWarnings(True)

from threading import Thread
import queue
import json

url_queue = queue.Queue()
result_queue = queue.Queue()
xiaoqu = []


class Xiaoqu(Thread):
    def __init__(self,i):
        Thread.__init__(self)
        self.i = i
        self.result = []

    def run(self) -> None:

        i = self.i
        url = 'https://sh.lianjia.com/xiaoqu/jiading/pg%d/' % i
        print(url)
        proxies = {
            "https":"http://10.8.8.24:4002"
        }
        content = ''
        for jj in range(10):
            print('第一次%d'%jj)
            res = requests.get(url,proxies=proxies,headers ={
            },verify = False)
            content = res.content.decode('utf8')
            if '上海嘉定' in content:
                break
        liList = PyQuery(content).find('.listContent li')
        if len(liList)==0:
            print('没有了')
            return
        for qu in liList:
            detail = PyQuery(qu).find('.totalSellCount')
            name = detail.attr('title')
            count = detail.find('span').html()
            print(name,count)
            self.result.append({"name": name, "count": count})


aa = []
for i in range(1,50):
    bb = Xiaoqu(i)
    aa.append(bb)
    bb.start()

for p in aa:
    p.join()

for p in aa:
    xiaoqu.extend(p.result)


total_count = 0
for xi in xiaoqu:
    total_count += int(xi['count'])


print(len(xiaoqu),total_count)