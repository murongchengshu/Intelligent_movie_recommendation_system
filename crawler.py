#! /usr/bin/python
# -*- coding: UTF-8 -*-
import requests
import json
from bs4 import BeautifulSoup
#数据库采用sqlite
import sqlite3
import re
import db_function
from lxml import html
import re
def pachong(num_pages=1, progress_callback=None):
    url='https://www.hdmoli.pro/mlist/index1-{}.html'.format(num_pages)
    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0'

    }
    req=requests.get(url=url,headers=headers)
    if req.status_code==200:
        html_doc=req.content.decode('utf-8')
        soup=BeautifulSoup(html_doc,'lxml')
        lis=soup.find_all('div',class_='myui-vodlist__box')
        i=0
        for li in lis:
            try:
                i+=1
                new_url=li.find('a')['href']
                new_url='https://www.hdmoli.pro{}'.format(new_url)
                response=requests.get(new_url,headers=headers)
                if response.status_code==200:
                    html_doc=response.content.decode('utf-8')
                    soup=BeautifulSoup(html_doc,'lxml')
                    comment=soup.find_all('p',class_='text-muted col-pd')[0].get_text()
                    description = re.search(r'剧情：(.*)', comment).group(1)
                score=li.find('span',class_='pic-tag pic-tag-top').get_text().strip()
                name=li.find('div',class_='myui-vodlist__detail').find('a').get_text().strip()
                ty_pe=li.find('p',class_='text text-overflow text-muted hidden-xs').get_text().strip()
                ty_pe=re.sub(r'^\d{4}/',' ',ty_pe)
                db_function.insert_movie(name,score,ty_pe,description)
                print("爬取成功第{}部电影并成功导入到数据库".format(i))

            except :
                    continue
    else:
        print("数据爬取失败")