import requests

from pyquery import PyQuery
import logging
logging.captureWarnings(True)

from threading import Thread
import queue
import json
url_queue = queue.Queue()


xiaoqu = []

class Xiaoqu(Thread):
    def __init__(self,queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self) -> None:

        i = self.queue.get()
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

            xiaoqu.append({"name":name,"count":count})
            print(name,count)

for i in range(1,50):
    url_queue.put(i)


aa = []
for i in range(0,49):
    bb = Xiaoqu(url_queue)
    aa.append(bb)
    bb.start()

for p in aa:
    p.join()

total_count = 0
for xi in xiaoqu:
    total_count += int(xi['count'])


print(len(xiaoqu),total_count)