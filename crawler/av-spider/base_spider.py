# coding=utf-8

import json
import random
import requests
import time
from urllib.parse import urlparse


class BaseSpider(object):
    session = requests.session()

    def __init__(self, baseUrl, houndUrl, startUrl):
        self.baseUrl = baseUrl
        self.houndUrl = houndUrl
        self.startUrl = startUrl

        pr = urlparse(self.startUrl)
        self.host = pr.scheme + '://' + pr.netloc
        self.source = '' # 子类必须设置

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
            'Referer': self.host,
            'User-Agent': userAgents[0]
        }
        return headers

    def printException(self, e):
        print('Exception occurs at line %s' % (e.__traceback__.tb_lineno.__str__()))
        print(e)

    def request(self, url, tries=1):
        if tries >= 10:
            print(url, 'tries>=10')
            return False
        try:
            r = self.session.get(url, headers=self.getHeaders())
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
        """子类必须实现此方法"""
        raise NotImplementedError("子类必须实现 start 方法")

    def parseList(self, url):
        """子类必须实现此方法"""
        raise NotImplementedError("子类必须实现 parseList 方法")

    def parseMovie(self, item):
        """子类必须实现此方法"""
        raise NotImplementedError("子类必须实现 parseMovie 方法")

    def sendMovieData(self, movie):
        movies = [movie]
        data = {
            'type': 'movie',
            'movies': json.dumps(movies)
        }
        self.hound(data)
