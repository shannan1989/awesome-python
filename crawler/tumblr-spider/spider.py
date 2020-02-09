# coding=utf-8

import datetime
import os
import sqlite3
import time
from urllib import parse

import requests
from fake_useragent import UserAgent
from lxml import etree

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

ua = UserAgent()


class TumblrSpider(object):
    def __init__(self, config, savepath, storepath, database):
        self.config = config
        self.savepath = savepath
        self.storepath = storepath
        self.con = sqlite3.connect(database)

    def __del__(self):
        if self.con:
            self.con.close()

    def start(self):
        try:
            url = 'https://%s.tumblr.com/api/read' % (self.config['user'])
            r = requests.get(url, headers={'User-Agent': ua.random})
            print('%s %s' % (r.status_code, url))
            if r.status_code != 200:
                return
            else:
                root = ET.fromstring(r.content)

                tumblelog = root.find('tumblelog')
                title = tumblelog.attrib.get('title')
                if title is None:
                    title = tumblelog.attrib.get('name')

                subdirectory = title

                posts = root.find('posts')

                post_items = posts.findall('post')
                post_items.reverse()
                for post in post_items:
                    update_time = (float)(post.attrib.get('unix-timestamp'))

                    for photo in post.iter('photo-url'):
                        if photo.attrib.get('max-width') == '1280':
                            self.save_item(
                                photo.text, subdirectory, update_time)

                    for caption in post.findall('photo-caption'):
                        for figure in etree.HTML(caption.text).xpath("//figure[@class='tmblr-full']//img/@src"):
                            self.save_item(figure, subdirectory, update_time)

                    for caption in post.findall('video-caption'):
                        for figure in etree.HTML(caption.text).xpath("//figure[@class='tmblr-full']//img/@src"):
                            self.save_item(figure, subdirectory, update_time)

                    for body in post.findall('regular-body'):
                        for figure in etree.HTML(body.text).xpath("//figure[@class='tmblr-full']//img/@src"):
                            self.save_item(figure, subdirectory, update_time)

        except Exception as e:
            print('Exception occurs at line ' +
                  e.__traceback__.tb_lineno.__str__(), e)

    def save_item(self, url, subdirectory, update_time):
        r = parse.urlparse(url)
        ts = r.path.split('/')
        file_name = ts.pop()

        file_ext = os.path.join(self.storepath, subdirectory, file_name)
        if os.path.exists(file_ext):
            os.utime(file_ext, (update_time, update_time))
            return

        date = datetime.datetime.fromtimestamp(
            update_time).strftime("%Y-%m-%d")
        file_path = os.path.join(self.savepath, subdirectory, date, file_name)
        if os.path.exists(file_path):
            os.utime(file_path, (update_time, update_time))
            return

        # 超过一定时间的内容，不再爬取
        if self.config['crawl_all'] is False:
            if time.time() - update_time > 3600 * 24 * 30:
                return

        file_dir = os.path.join(self.savepath, subdirectory, date)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        try:
            print("Fetching %s" % (url))
            ir = requests.get(url, timeout=3000)
            if ir.status_code == 200:
                with open(file_path, 'wb') as w:
                    w.write(ir.content)
                w.close()
                os.utime(file_path, (update_time, update_time))
                print("Saved to %s" % (file_path))
        except Exception as e:
            print("Save Failed: %s" % (e))
