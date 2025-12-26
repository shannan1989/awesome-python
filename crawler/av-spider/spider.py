# coding=utf-8

import json
import random
import requests
import time
from datetime import datetime
from itertools import count
from lxml import etree
from multiprocessing.dummy import Pool
from urllib.parse import urlparse

session = requests.session()

class JavBusSpider(object):
    def __init__(self, baseUrl, houndUrl, startUrl):
        self.baseUrl = baseUrl
        self.houndUrl = houndUrl
        self.startUrl = startUrl

        pr = urlparse(self.startUrl)
        self.host = pr.scheme + '://' + pr.netloc

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
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.javbus.com',
            'User-Agent': userAgents[0]
        }
        return headers

    def printException(self, e):
        print('Exception occurs at line %s' %
              (e.__traceback__.tb_lineno.__str__()))
        print(e)

    def request(self, url, tries=1):
        if tries >= 10:
            print(url, 'tries>=10')
            return False
        try:
            session.cookies.set('existmag', 'all', path='/', domain='www.javbus.com')
            r = session.get(url, headers=self.getHeaders())
            print('%s %s' % (r.status_code, url))
            if r.status_code != 200:
                time.sleep(5)
                return self.request(url, tries + 1)

            return r
        except Exception as e:
            print(url, e)
            time.sleep(5)
            return self.request(url, tries + 1)

    def hound(self, data):
        try:
            r = requests.post(self.houndUrl, data, headers=self.getHeaders())
            print(r.content)
        except Exception as e:
            self.printException(e)

    def start(self):
        r = requests.get(self.baseUrl, headers=self.getHeaders())

        data = json.loads(r.text)
        self.ids = data.get('ids')
        self.stars = data.get('stars')
        self.studios = data.get('studios')
        self.series = data.get('series')
        self.genres = data.get('genres')

        self.parseList(self.startUrl)

        for star in self.stars:
            if star['subscribe'] < 1:
                continue
            if len(star['id']) > 6:
                continue
            print('开始爬取女优 ' + star['name'])
            url = self.host + '/star/' + star['id']
            self.parseList(url)

        for studio in self.studios:
            if studio['status'] < 1:
                continue
            if len(studio['id']) > 6:
                continue
            print('开始爬取片商 ' + (studio.get('aka') or studio['name']))
            url = self.host + '/studio/' + studio['id']
            # self.parseList(url)

        for series in self.series:
            if series['status'] < 1:
                continue
            if len(series['id']) > 6:
                continue
            print('开始爬取系列 ' + (series.get('aka') or series['name']))
            url = self.host + '/series/' + series['id']
            self.parseList(url)
        
        for genre in self.genres:
            if genre['status'] < 1:
                continue
            if len(genre['id']) > 6:
                continue
            print('开始爬取类别 ' + genre['name'])
            url = self.host + '/genre/' + genre['id']
            # self.parseList(url)

    def parseList(self, url):
        r = self.request(url)
        if r == False:
            return

        pr = urlparse(url)

        html = etree.HTML(r.content)

        next = False
        movies = []
        items = html.xpath("//div[@class='item']//a[@class='movie-box']")
        for _item in items:
            dates = _item.xpath(".//div[@class='photo-info']//date")
            if len(dates) == 2:
                date1 = datetime.strptime(dates[1].text, "%Y-%m-%d")
                date2 = datetime.strptime('2023-12-15', "%Y-%m-%d")
                if date1 < date2:
                    continue
                else:
                    next = True

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
        nextpage = html.xpath("//div/ul/li/a[@id='next']")
        if len(nextpage) > 0:
            href = nextpage[0].attrib.get('href')
            if href.startswith("/"):
                href = pr.scheme + '://' + pr.netloc + href
            print('下一页：' + href)
            self.parseList(href)
        else:
            print('没有下一页')

    def parseMovie(self, item):
        url = item['url']
        r = self.request(url)
        if r == False:
            return

        html = etree.HTML(r.content)

        movie = {
            'id': '',
            'source': 'javbus',
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
        movie['poster'] = html.xpath("//a[@class='bigImage']/img")[0].attrib.get('src')
        if movie['poster'].startswith("/"):
            movie['poster'] = self.host + movie['poster']

        sample_images = html.xpath("//div[@id='sample-waterfall']//a[@class='sample-box']")
        for _img in sample_images:
            movie['samples'].append(_img.attrib.get('href'))

        infos = html.xpath("//div[@class='col-md-3 info']/p")
        for _info in infos:
            nodes = _info.xpath('node()')
            if len(nodes) < 2:
                continue
            if type(nodes[0]) == etree._Element and nodes[0].text == '識別碼:':
                movie['serial_number'] = nodes[2].text
            if type(nodes[0]) == etree._Element and nodes[0].text == '發行日期:':
                movie['release_date'] = str(nodes[1]).strip()
            if type(nodes[0]) == etree._Element and nodes[0].text == '長度:':
                movie['duration'] = str(nodes[1]).strip()

        star_names = {}
        genres = html.xpath("//div[@class='col-md-3 info']/p/span[@class='genre']//a")
        for genre in genres:
            href = genre.attrib.get('href')
            if 'star' in href:
                star_id = href.split('/').pop()
                star_name = genre.text
                star_names[star_id] = star_name
                continue
            if 'genre' not in href:
                continue
            genre_id = href.split('/').pop()
            genre_name = genre.text
            movie['genres'].append({'id': genre_id, 'name': genre_name})

        stars = html.xpath("//div[@id='avatar-waterfall']/a")
        for _star in stars:
            star_id = _star.attrib.get('href').split('/').pop()
            if star_names[star_id] is not None:
                star_name = star_names[star_id]
            else:
                try:
                    star_name = _star.xpath(".//span")[0].text
                except Exception as e:
                    star_name = ''
                    self.printException(e)
            star_avatar = _star.xpath(".//img")[0].attrib.get('src')
            if 'nowprinting' in star_avatar:
                star_avatar = ''
            if star_avatar.startswith("/"):
                star_avatar = self.host + star_avatar
            star = {'id': star_id, 'source': 'javbus', 'name': star_name, 'avatar': star_avatar}
            movie['stars'].append(star)

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
            self.parseList(url, star['subscribe'] >= 1)

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
            'source': 'avmoo',
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
            try:
                star_name = _star.xpath(".//span")[0].text
            except Exception as e:
                star_name = ''
                self.printException(e)
            star_avatar = _star.xpath(".//img")[0].attrib.get('src')
            if 'nowprinting' in star_avatar:
                star_avatar = ''
            star = {'id': star_id, 'source': 'avmoo', 'name': star_name, 'avatar': star_avatar}
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
