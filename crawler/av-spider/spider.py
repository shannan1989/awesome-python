# coding=utf-8

import json
import random
import requests
import time
from itertools import count
from lxml import etree
from multiprocessing.dummy import Pool
from urllib.parse import urlparse


class AvmooSpider(object):
    def __init__(self, baseUrl, houndUrl, startUrl):
        self.baseUrl = baseUrl
        self.houndUrl = houndUrl

        pr = urlparse(startUrl)
        self.host = pr.scheme + '://' + pr.netloc

        # 需要爬取的列表页
        self.urls = [
            startUrl
        ]

    def getHeaders(self):
        userAgents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edge/18.17763'
        ]
        random.shuffle(userAgents)
        headers = {
            'User-Agent': userAgents[0]
        }
        return headers

    def hound(self, data):
        try:
            r = requests.post(self.houndUrl, data, headers=self.getHeaders())
            print(r.content)
        except Exception as e:
            self.printException(e)

    def printException(self, e):
        print('Exception occurs at line %s' %
              (e.__traceback__.tb_lineno.__str__()))
        print(e)

    def start(self):
        r = requests.get(self.baseUrl, headers=self.getHeaders())

        data = json.loads(r.text)
        self.ids = data.get('ids')
        self.stars = data.get('stars')

        for url in self.urls:
            self.parseList(url, True)

        for star in self.stars:
            print('开始爬取女优 ' + star['name'])
            url = self.host + '/cn/star/' + star['id']
            self.parseList(url, star['subscribe'] == 1)

    def request(self, url, tries=1):
        if tries >= 10:
            print(url, 'tries>=10')
            return False
        try:
            r = requests.get(url, headers=self.getHeaders())
            print('%s %s' % (r.status_code, url))
            if r.status_code != 200:
                time.sleep(5)
                return self.request(url, tries + 1)

            return r
        except Exception as e:
            print(url, e)
            time.sleep(5)
            return self.request(url, tries + 1)

    def parseList(self, url, next, tries=1):
        r = self.request(url)
        if r == False:
            return

        pr = urlparse(url)

        html = etree.HTML(r.content)

        # 演员信息
        if ('/star/' in url) & ('page' not in url):
            star_id = url.split('/').pop()
            _infos = []
            infos = html.xpath(
                '//div[@class="avatar-box"]//div[@class="photo-info"]/p')
            for i in infos:
                if i.text is not None:
                    _infos.append(i.text)

            data = {
                'type': 'star',
                'star_id': star_id,
                'infos': json.dumps(_infos)
            }
            self.hound(data)

            if next == False:
                time.sleep(1)
                return

        movies = []
        items = html.xpath("//div[@class='item']//a[@class='movie-box']")
        for _item in items:
            href = _item.attrib.get('href')
            if href.startswith("//"):
                href = pr.scheme + ':' + href

            movie_id = href.split('/').pop()
            if (movie_id in self.ids):
                continue

            thumb = ''
            thumbs = _item.xpath(".//div[@class='photo-frame']//img")
            for _thumb in thumbs:
                thumb = _thumb.attrib.get('src')

            movies.append({'thumb': thumb, 'url': href})

        if len(movies) > 0:
            pool = Pool(processes=2)
            pool.map(self.parseMovie, movies)
            pool.close()
            pool.join()

        time.sleep(2)

        if next == False:
            return

        # 下一页
        nextpage = html.xpath("//div/ul/li/a[@name='nextpage']")
        if len(nextpage) > 0:
            href = nextpage[0].attrib.get('href')
            if href.startswith("/"):
                href = pr.scheme + '://' + pr.netloc + href
            print('next page')
            self.parseList(href, next)

    def parseMovie(self, item, tries=1):
        url = item['url']
        r = self.request(url)
        if r == False:
            return

        html = etree.HTML(r.content)

        movie = {
            'id': '',
            'title': '',
            'poster': '',
            'serial_number': '',
            'samples': [],
            'duration': '',
            'release_date': '1990-01-01',
            'stars': [],
            'directors': [],
            'genres': [],
            'series': [],
            'studios': [],
            'labels': []
        }

        movie['id'] = url.split('/').pop()
        movie['title'] = html.xpath("//div[@class='container']/h3")[0].text
        movie['poster'] = html.xpath(
            "//a[@class='bigImage']/img")[0].attrib.get('src')

        sample_images = html.xpath(
            "//div[@id='sample-waterfall']//a[@class='sample-box']")
        for _img in sample_images:
            movie['samples'].append(_img.attrib.get('href'))

        stars = html.xpath("//div[@id='avatar-waterfall']/a")
        for _star in stars:
            star_id = _star.attrib.get('href').split('/').pop()
            star_name = _star.xpath(".//span")[0].text
            star_avatar = _star.xpath(".//img")[0].attrib.get('src')
            if 'nowprinting' in star_avatar:
                star_avatar = ''
            star = {'id': star_id, 'name': star_name, 'avatar': star_avatar}
            movie['stars'].append(star)

        infos = html.xpath("//div[@class='col-md-3 info']/p")
        for _info in infos:
            nodes = _info.xpath('node()')
            if len(nodes) < 2:
                continue
            if nodes[0].text == '识别码:':
                movie['serial_number'] = nodes[2].text
            if nodes[0].text == '发行时间:':
                movie['release_date'] = str(nodes[1]).strip()
            if nodes[0].text == '长度:':
                movie['duration'] = str(nodes[1]).strip()

        genres = html.xpath(
            "//div[@class='col-md-3 info']/p/span[@class='genre']/a")
        for genre in genres:
            genre_id = genre.attrib.get('href').split('/').pop()
            genre_name = genre.text
            movie['genres'].append({'id': genre_id, 'name': genre_name})

        infos = html.xpath("//div[@class='col-md-3 info']/p/a")
        for info in infos:
            href = info.attrib.get('href')
            info_id = href.split('/').pop()
            info_name = info.text
            if 'series' in href:
                movie['series'].append({'id': info_id, 'name': info_name})
                continue
            if 'label' in href:
                movie['labels'].append({'id': info_id, 'name': info_name})
                continue
            if 'studio' in href:
                movie['studios'].append({'id': info_id, 'name': info_name})
                continue
            if 'director' in href:
                movie['directors'].append({'id': info_id, 'name': info_name})
                continue
            print(info_id, info_name, href)

        movies = []
        movies.append(movie)
        data = {
            'type': 'movie',
            'movies': json.dumps(movies)
        }
        self.hound(data)

        time.sleep(1)
