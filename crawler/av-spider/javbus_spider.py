# coding=utf-8

import json
import time
from datetime import datetime
from lxml import etree
from multiprocessing.dummy import Pool

from base_spider import BaseSpider


class JavBusSpider(BaseSpider):
    def __init__(self, baseUrl, houndUrl, startUrl):
        super(JavBusSpider, self).__init__(baseUrl, houndUrl, startUrl)
        self.source = 'javbus'

        self.session.cookies.set('existmag', 'all', path='/', domain='www.javbus.com')

    def start(self):
        r = self.request(self.baseUrl)
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
        if r is False:
            return

        html = etree.HTML(r.content)

        goNext = False
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
                    goNext = True

            href = self.parseHref(_item.attrib.get('href'), url)

            movie_id = href.split('/').pop()
            if movie_id in self.ids:
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

        if goNext == False:
            return

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

        html = etree.HTML(r.content)

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

        movie['id'] = url.split('/').pop()
        movie['title'] = html.xpath("//div[@class='container']/h3")[0].text
        movie['poster'] = self.parseHref(html.xpath("//a[@class='bigImage']/img")[0].attrib.get('src'), url)

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
            if star_id in star_names:
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
            else:
                star_avatar = self.parseHref(star_avatar, url)
            star = {'id': star_id, 'source': self.source, 'name': star_name, 'avatar': star_avatar}
            movie['stars'].append(star)

        infos = html.xpath("//div[@class='col-md-3 info']/p/a")
        for info in infos:
            href = info.attrib.get('href')
            info_id = href.split('/').pop()
            info_name = info.text
            if 'series' in href:
                movie['series'].append({'id': info_id, 'name': info_name})
            elif 'label' in href:
                movie['labels'].append({'id': info_id, 'name': info_name})
            elif 'studio' in href:
                movie['studios'].append({'id': info_id, 'name': info_name})
            elif 'director' in href:
                movie['directors'].append({'id': info_id, 'name': info_name})

        self.sendMovieData(movie)
        time.sleep(1)
