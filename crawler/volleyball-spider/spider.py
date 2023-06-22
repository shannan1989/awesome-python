import abc
import json
import random
import time

import requests
from bs4 import BeautifulSoup, Comment


class VolleyballSpider(metaclass=abc.ABCMeta):
    houndUrl = ''

    @abc.abstractmethod
    def start(self):
        pass

    def hound(self, data):
        try:
            r = requests.post(self.houndUrl, data, headers=self.getHeaders())
            print(r.content)
        except Exception as e:
            self.printException(e)

    def getHeaders(self):
        userAgents = [
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

    def printException(self, e):
        print('Exception occurs at line %s' %
              (e.__traceback__.tb_lineno.__str__()))
        print(e)


class VolleyChinaSpider(VolleyballSpider):
    def __init__(self):
        self.url = "http://www.volleychina.org/allnews/index.html"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url):
        response = requests.get(url, headers=self.getHeaders())
        soup = BeautifulSoup(response.content, "html.parser")

        news = []
        for item in soup.find_all('li', class_='new-detail'):
            article = {
                'source': 'volleychina',
                'title': '',
                'author': '',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': ''
            }

            title_ = item.select_one('a.new-title')
            if title_ is None:
                continue
            article['url'] = title_.get('href')
            article['title'] = title_.text

            author_ = item.select_one('p.new-footer-left span:nth-child(1)')
            article['author'] = author_.text

            desc_ = item.select_one('span.new-info p')
            for a in desc_.find_all('a'):
                a.extract()
            article['desc'] = desc_.get_text(strip=True)

            poster_ = item.select_one('span.new-info a img')
            if poster_ is not None:
                article['poster'] = poster_.get('src')

            article['content'] = self.parse_item(article['url'])

            time_ = item.select_one('p.new-footer-left span:nth-child(2)')
            article['publish_time'] = time_.text

            news.append(article)
            if len(news) == 10:
                self.hound({'news': json.dumps(news)})
                news = []
                time.sleep(1)

        self.hound({'news': json.dumps(news)})

    def parse_item(self, url):
        r = requests.get(url, headers=self.getHeaders())
        print('%s %s' % (r.status_code, url))
        soup = BeautifulSoup(r.content, "html.parser")

        # Remove all comments from the HTML string
        for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
            comment.extract()

        content = soup.find("div", class_="detail-context").prettify()
        return content
