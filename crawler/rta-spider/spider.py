# coding=utf-8

import json
import os
import time
from multiprocessing import Pool
from urllib import parse

import requests
from fake_useragent import UserAgent
from lxml import etree

ua = UserAgent()


class RtaSpider(object):
    def __init__(self, host, name, savepath, storepath):
        self.host = host
        self.name = name
        self.savepath = savepath
        self.storepath = storepath

    def start(self):
        try:
            self.parse_list(self.host+'/videos')
        except Exception as e:
            print('Exception occurs at line %s' %
                  (e.__traceback__.tb_lineno.__str__()), e)

    def parse_list(self, url):
        r = requests.get(url, headers={'User-Agent': ua.random})
        print('%s %s' % (r.status_code, url))
        if r.status_code != 200:
            return
        else:
            html = etree.HTML(r.content)

            # 获取列表
            items = html.xpath("//a[@class='sc-1z0w6pb-8 klffOV']/@href")
            items.extend(html.xpath("//a[@class='blrxs5-3 eWSdEW']/@href"))
            pool = Pool(processes=len(items))
            pool.map(self.parse_item, items)
            pool.close()
            pool.join()

            # 获取下一页
            exp = u'//a[@class="sc-8bfwvf-2 sc-8bfwvf-8 ehwsox active"]/@href'
            pages = html.xpath(exp)
            if len(pages) == 2:
                next_page = pages[1]
            else:
                next_page = pages[0]
            if next_page != 'javascript:void(0);':
                print(next_page)
                # self.parse_list(self.host + next_page)

    def parse_item(self, url):
        url = url.replace('?autoplay=true', '')
        if url.startswith('/'):
            url = self.host+url
        r = requests.get(url, headers={'User-Agent': ua.random})
        print('%s %s' % (r.status_code, url))
        if r.status_code != 200:
            return
        else:
            html = etree.HTML(r.content)

            info = json.loads(html.xpath(
                "//script[@type='application/ld+json']")[0].text)
            name = info['name']
            post_time = int(time.mktime(time.strptime(
                info['uploadDate'], "%Y-%m-%dT%H:%M:%S.000Z")))
            date = time.strftime("%Y-%m-%d", time.localtime(post_time))

            subdirectory = date + ' ' + name

            file_dir = os.path.join(self.savepath, self.name, subdirectory)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            t = ''
            for s in html.xpath("//script"):
                if 'window.__INITIAL_STATE__ =' in s.text:
                    a = s.text.split('window.__APOLLO_STATE__')
                    t = a[0]
                    t = t.replace('window.__INITIAL_STATE__ =', '')
                    t = t.replace('\n', '')
                    t = t.replace(' ', '')
                    t = t[:-1]
                    break
            info = json.loads(t)

            info.pop('error')
            info.pop('locale')
            info.pop('meta')
            info.pop('quickSearch')
            info.pop('analytics')
            info.pop('flashNotifications')
            info.pop('itsUpAds')
            info.pop('location')
            info.pop('promotions')
            info.pop('redirection')
            info.pop('modals')
            info.pop('models')
            info.pop('experiments')
            info.pop('videoPlayer')
            info.pop('document')
            info.pop('featuredVideos')

            page = info['page']
            pathname = page['location']['pathname']
            data = page['data'][pathname]['data']

            pictureset = data['pictureset']
            for pset in pictureset:
                for item in pset['main']:
                    self.save_item(item['src'], subdirectory, post_time)

            # video = data['video']
            # posters = video['previews']['poster']
            # for p in posters:
            #     if p['height'] == 1080:
            #         self.save_item(p['src'], subdirectory, post_time)

            # posters = video['images']['poster']
            # for p in posters:
            #     if p['height'] == 1080:
            #         self.save_item(p['highdpi']['3x'], subdirectory, post_time)

    def save_item(self, url, subdirectory, update_time):
        r = parse.urlparse(url)
        ts = r.path.split('/')
        file_name = ts.pop()

        file_ext = os.path.join(self.storepath, self.name,
                                subdirectory, file_name)
        if os.path.exists(file_ext):
            os.utime(file_ext, (update_time, update_time))
            return

        file_path = os.path.join(self.savepath, self.name,
                                 subdirectory, file_name)
        if os.path.exists(file_path):
            os.utime(file_path, (update_time, update_time))
            return

        try:
            ir = requests.get(url, timeout=3000)
            if ir.status_code == 200:
                open(file_path, 'wb').write(ir.content)
                print("Saved to %s" % (file_path))
        except Exception as e:
            print("Save Failed: %s" % (e))
