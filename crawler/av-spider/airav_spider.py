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
        """解析 AirAv 影片详情并提交结构化数据。"""
        url = item['url']
        r = self.request(url)
        if r is False:
            return

        html = etree.HTML(r.content.decode('utf-8', errors="ignore"))

        # 1. 组装影片基础信息，并解析描述和播放地址
        movie = self._newMovie()

        movie['id'] = item['id']
        movie['title'] = html.xpath("//div[@class='video-title my-3']/h1")[0].text
        movie['poster'] = item['thumb']
        movie['desc'], movie['video_url'] = self._parse_video_metadata(html, url)

        # 2. 解析演员及头像信息
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

        # 3. 解析番号、发布日期及分类关系
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

        # 4. 提交单条影片数据
        self.sendMovieData(movie)
        time.sleep(1)

    def _parse_video_metadata(self, html, page_url):
        """从详情页解析影片描述和视频播放地址。"""
        description = str(html.xpath(
            "string((//div[contains(@class, 'video-info')]/p)[1])"
        )).strip()
        video_url = ''

        # 1. 从 JSON-LD 获取播放地址，并在正文描述缺失时作为回退
        for raw_metadata in html.xpath("//script[@type='application/ld+json']/text()"):
            try:
                metadata = json.loads(raw_metadata)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(metadata, dict) or metadata.get('@type') != 'VideoObject':
                continue
            description = description or str(metadata.get('description') or '').strip()
            video_url = str(metadata.get('contentUrl') or '').strip()
            if video_url:
                break

        # 2. 结构化播放地址缺失时，回退到 video source
        if not video_url:
            video_url = str(html.xpath(
                "string((//video[@id='video_player']//source/@src)[1])"
            )).strip()

        if video_url:
            video_url = self.parseHref(video_url, page_url)

        return description, video_url
