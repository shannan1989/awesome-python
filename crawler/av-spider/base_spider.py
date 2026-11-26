# coding=utf-8

import json
import random
import requests
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlsplit


class BaseSpider(object):
    # 重试无法恢复的 4xx 状态码，收到后只放弃本次请求
    _NO_RETRY_STATUS = (400, 401, 403, 404, 410)
    # 地区/法务限制通常作用于整个站点，命中后熔断本轮剩余请求
    _BLOCKED_STATUS = (451,)

    def __init__(self, baseUrl, houndUrl, startUrl):
        self.session = requests.session()

        # 站点是否已被判定为地区/法务限制，用于熔断本轮剩余请求
        self.blocked = False

        self.baseUrl = baseUrl
        self.houndUrl = houndUrl
        self.startUrl = startUrl

        pr = urlparse(self.startUrl)
        self.host = pr.scheme + '://' + pr.netloc
        self.source = '' # 子类必须设置

    def getBaseUrl(self) -> str:
        """返回带有当前爬虫来源的同步数据地址，保留其他查询参数。"""
        url = urlsplit(self.baseUrl)
        query = [(key, value) for key, value in parse_qsl(url.query, keep_blank_values=True) if key != 'source']
        query.append(('source', self.source))
        return url._replace(query=urlencode(query)).geturl()

    def getHeaders(self):
        userAgents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edge/18.17763'
        ]
        headers = {
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host,
            'User-Agent': random.choice(userAgents)
        }
        return headers

    def printException(self, e):
        print('Exception occurs at line %s' % (e.__traceback__.tb_lineno.__str__()))
        print(e)

    def parseHref(self, href: str, base_url: str) -> str:
        """
        将页面中获取的链接解析为绝对 URL。
        支持三种格式：
          - 以 http(s):// 开头的完整链接，直接返回
          - 以 // 开头的协议相对链接，补全当前协议
          - 以 / 开头的根相对链接，补全协议 + 域名
        
        Args:
            href (str): 从页面中提取的原始链接
            base_url (str): 当前页面的完整 URL，用于补全相对链接
            
        Returns:
            str: 转换后的绝对链接
        """
        return urljoin(base_url, href)

    def request(self, url, tries=1):
        # 1. 站点已确认被拦截时直接放弃，避免对后续每个列表页、详情页重复空转
        if self.blocked:
            return False
        if tries > 10:
            print(url, 'tries=10')
            return False
        try:
            r = self.session.get(url, headers=self.getHeaders(), timeout=30)
            print('%s %s' % (r.status_code, url))

            # 2. 地区/法务限制作用于整个站点，重试无意义，直接熔断本轮
            if r.status_code in self._BLOCKED_STATUS:
                self.blocked = True
                print('%s 返回 %s（地区/法务限制），本轮跳过 %s' % (url, r.status_code, self.source))
                return False

            # 3. 其余 4xx 重试也无法恢复，只放弃本次请求，不影响后续地址
            if r.status_code in self._NO_RETRY_STATUS:
                print('%s 返回 %s，不再重试' % (url, r.status_code))
                return False

            # 4. 5xx、429 等临时性错误仍按间隔重试
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

    def _newMovie(self) -> dict:
        return {
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
