# coding=utf-8

import json
import time
from lxml import etree
from multiprocessing.dummy import Pool
from urllib.parse import urlparse, parse_qs

from base_spider import BaseSpider


class AirAvSpider(BaseSpider):
    def __init__(self, baseUrl, houndUrl, startUrl):
        super(AirAvSpider, self).__init__(baseUrl, houndUrl, startUrl)
        self.source = 'airav'

    def start(self):
        r = self.request(self.baseUrl)

        data = json.loads(r.text)
        self.ids = data.get('ids')
        self.stars = data.get('stars')
        self.studios = data.get('studios')
        self.series = data.get('series')
        self.genres = data.get('genres')

        self.parseList(self.startUrl)

    def parseList(self, url):
        r = self.request(url)
        if r is False:
            return

        html = etree.HTML(r.content.decode('utf-8', errors="ignore"))

        movies = []
        items = html.xpath("//div[@class='oneVideo-top']//a")
        for _item in items:
            href = self.parseHref(_item.attrib.get('href'), url)

            query_params = parse_qs(urlparse(href).query)
            movie_id = query_params.get("hid", [None])[0]
            if movie_id in self.ids:
                continue

            thumb = ''
            thumbs = _item.xpath(".//img")
            for _thumb in thumbs:
                thumb = self.parseHref(_thumb.attrib.get('src'), url)

            movies.append({'id': movie_id, 'thumb': thumb, 'url': href})

        if len(movies) > 0:
            pool = Pool(processes=2)
            pool.map(self.parseMovie, movies)
            pool.close()
            pool.join()

        time.sleep(2)

        # 下一页
        nextpage = html.xpath("//div/ul/li/a[@id='next']")
        if len(nextpage) > 0:
            href = self.parseHref(nextpage[0].attrib.get('href'), url)
            print('下一页：' + href)
            self.parseList(href)
        else:
            print('没有下一页')

    def parseMovie(self, item):
        url = item['url']
        r = self.request(url)
        if r is False:
            return

        html = etree.HTML(r.content.decode('utf-8', errors="ignore"))

        movie = {
            'id': '',
            'source': self.source,
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

        movie['id'] = item['id']
        movie['title'] = html.xpath("//div[@class='video-title my-3']/h1")[0].text
        movie['des'] = html.xpath("//div[@class='video-info']/p")[0].text
        movie['poster'] = item['thumb']

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
            else:
                star_avatar = self.parseHref(star_avatar, url)
            star = {'id': star_id, 'source': self.source, 'name': star_name, 'avatar': star_avatar}
            movie['stars'].append(star)

        infos = html.xpath("//div/ul[@class='list-group']/li")
        for _info in infos:
            nodes = _info.xpath('node()')
            if len(nodes) < 2:
                continue
            if type(nodes[0]) == etree._ElementUnicodeResult and str(nodes[0]) == '番号：':
                movie['serial_number'] = nodes[1].text
            # TODO

        video_info = html.xpath("//div[@class='video-item']/div[@class='me-4']/text()")
        if len(video_info) > 0:
            movie['release_date'] = video_info[0]

        genres = html.xpath("//div[@class='col-md-3 info']/p/span[@class='genre']//a")
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

        self.sendMovieData(movie)
        time.sleep(1)
