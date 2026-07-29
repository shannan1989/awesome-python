# coding=utf-8

import json
import re
import time
from lxml import etree
from multiprocessing.dummy import Pool
from urllib.parse import urlparse, parse_qs

from base_spider import BaseSpider


class AirAvSpider(BaseSpider):
    def __init__(self, baseUrl, houndUrl, startUrl):
        super(AirAvSpider, self).__init__(baseUrl, houndUrl, startUrl)
        self.source = 'airav'
        self.max_pages = 10

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
        """解析 AirAv 列表页，并持续抓取后续分页。"""
        pages_crawled = 0
        while url:
            # 1. 请求并解析当前列表页
            r = self.request(url)
            if r is False:
                return

            html = etree.HTML(r.content.decode('utf-8', errors="ignore"))

            # 2. 过滤已采集影片，并并发抓取详情
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
            pages_crawled += 1

            if pages_crawled >= self.max_pages:
                print('已达到列表页抓取上限：%s' % self.max_pages)
                return

            # 3. 按页面提供的下一页链接继续抓取
            next_page_url = self._parse_next_page_url(html, url)
            if not next_page_url or next_page_url == url:
                print('没有下一页')
                return

            print('下一页：' + next_page_url)
            url = next_page_url

    def _parse_next_page_url(self, html, page_url):
        """解析 AirAv 列表页中的下一页地址。"""
        next_page_urls = html.xpath(
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' page ')]"
            "//a[normalize-space()='下一页' or normalize-space()='下一頁']/@href"
        )
        if not next_page_urls:
            return ''
        return self.parseHref(next_page_urls[0], page_url)

    def parseMovie(self, item):
        """解析 AirAv 影片详情并提交结构化数据。"""
        url = item['url']
        r = self.request(url)
        if r is False:
            return

        html = etree.HTML(r.content.decode('utf-8', errors="ignore"))

        # 1. 组装影片基础信息，并解析描述、播放地址和封面
        movie = self._newMovie()

        movie['id'] = item['id']
        movie['title'] = html.xpath("//div[@class='video-title my-3']/h1")[0].text
        desc, video_url, poster, duration = self._parse_video_metadata(html, url)
        movie['desc'] = desc.replace(movie['title'], '').strip()
        movie['video_url'] = video_url
        movie['poster'] = poster or item['thumb']
        movie['duration'] = 0 # 鉴于数据源的时长不准确，暂时设为0

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

        if movie['serial_number']:
            movie['title'] = movie['title'].replace(movie['serial_number'] + ' ' + movie['serial_number'], movie['serial_number']).strip()
        # 4. 提交单条影片数据
        self.sendMovieData(movie)
        time.sleep(1)

    def _parse_video_metadata(self, html, page_url):
        """从详情页解析影片描述、播放地址、封面和时长。"""
        description = str(html.xpath(
            "string((//div[contains(@class, 'video-info')]/p)[1])"
        )).strip()
        video_url = ''
        poster = ''
        duration = 0

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
            duration = self._parse_duration_minutes(metadata.get('duration'))
            thumbnail_urls = metadata.get('thumbnailUrl') or []
            if isinstance(thumbnail_urls, list) and thumbnail_urls:
                poster = str(thumbnail_urls[0]).strip()
            elif isinstance(thumbnail_urls, str):
                poster = thumbnail_urls.strip()
            if video_url:
                break

        # 2. 结构化播放地址缺失时，回退到 video source
        if not video_url:
            video_url = str(html.xpath(
                "string((//video[@id='video_player']//source/@src)[1])"
            )).strip()

        if video_url:
            video_url = self.parseHref(video_url, page_url)
        if poster:
            if poster.startswith('http'):
                pr = urlparse(poster, allow_fragments=False)
                if 'airav' in pr.netloc:
                    poster = pr.path
            poster = self.parseHref(poster, page_url)

        return description, video_url, poster, duration

    def _parse_duration_minutes(self, duration):
        """将 ISO 8601 视频时长转换为整数分钟。"""
        match = re.fullmatch(
            r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?',
            str(duration or '').strip()
        )
        if not match or not any(match.groups()):
            return 0

        hours, minutes, seconds = match.groups(default='0')
        return int(hours) * 60 + int(minutes) + int(float(seconds) // 60)
