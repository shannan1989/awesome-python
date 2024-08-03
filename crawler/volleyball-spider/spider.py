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

        if len(news) > 0:
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


class VolSportsSpider(VolleyballSpider):
    def __init__(self):
        self.url = "https://volsports.co/blog/category/news/"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url):
        r = requests.get(url, headers=self.getHeaders())
        print('%s %s' % (r.status_code, url))
        soup = BeautifulSoup(r.text, "html.parser")

        news = []
        for item in soup.select(".post"):
            article = {
                'source': 'volsports',
                'title': '',
                'author': '',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': ''
            }

            title_ = item.select_one("div.info a.name")
            article['url'] = title_.get('href')
            article['title'] = title_.text.strip()

            article['poster'] = item.select_one('div.img-wrap a img').get('src')

            time_ = item.select_one('div.info div.wrap a:nth-child(1)')
            article['publish_time'] = time_.text.strip()

            author_ = item.select_one('div.info div.wrap a:nth-child(2)')
            article['author'] = author_.text.strip()

            article['content'] = self.parse_item(article['url'])

            news.append(article)
            if len(news) == 5:
                self.hound({'news': json.dumps(news)})
                news = []

        if len(news) > 0:
            self.hound({'news': json.dumps(news)})

        # 下一页
        current_page = soup.select_one('ul.pagination li.active a').text
        if int(current_page) < 2:
            next_page = soup.select_one('ul.pagination li:last-child a')
            self.parse_list(next_page.get('href'))

    def parse_item(self, url):
        r = requests.get(url, headers=self.getHeaders())
        print('%s %s' % (r.status_code, url))
        soup = BeautifulSoup(r.content, "html.parser")

        content_ = soup.find("div", class_="post-content")

        for iframe in content_.find_all('iframe'):
            iframe.extract()

        # 删除每个h标签及其后面的内容
        for h in content_.find_all(['h2', 'h3']):
            if h.text.find('延伸閱讀') == -1:
                continue
            for tag in h.find_next_siblings():
                if tag.name == h.name:
                    break
                tag.extract()
            h.extract()

        content = content_.prettify()
        return content


class SportsVSpider(VolleyballSpider):
    def __init__(self):
        self.url = "https://www.sportsv.net/volleyball"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url, current_page=1):
        r = requests.get(url, headers=self.getHeaders())
        print('%s %s' % (r.status_code, url))
        soup = BeautifulSoup(r.text, "html.parser")

        news = []
        for item in soup.select("div.item_lish div.item"):
            article = {
                'source': 'sportsv',
                'title': '',
                'author': '',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': ''
            }

            title_ = item.select_one('h4 a')
            article['title'] = title_.text
            article['url'] = title_.get('href')
            article['poster'] = item.select_one('a div img.cover').get('src')
            article['author'] = item.select_one('a.author_name').text
            article['desc'] = item.select_one('p').text
            article['publish_time'] = item.select_one('div.date').text
            article['content'] = self.parse_item(article['url'])

            news.append(article)
            time.sleep(1)
            if len(news) == 1:
                self.hound({'news': json.dumps(news)})
                news = []

        if len(news) > 0:
            self.hound({'news': json.dumps(news)})

        # 下一页
        if current_page < 2:
            next_page = current_page + 1
            self.parse_list(self.url + '?page=' + str(next_page), next_page)

        # current_page = soup.select_one('div.pagination ul li.active a')
        # if int(current_page.text) < 5:
        #     next_page = soup.select_one('div.pagination ul li:last-child a')
        #     self.parse_list(next_page.get('href'))

    def parse_item(self, url):
        r = requests.get(url, headers=self.getHeaders())
        print('%s %s' % (r.status_code, url))
        soup = BeautifulSoup(r.content, "html.parser")

        content_ = soup.find("div", class_="article-content")

        for iframe in content_.find_all(['iframe', 'script']):
            iframe.extract()
        for tag in content_.find_all('div', class_='adv-article-content'):
            tag.extract()

        for tag in content_.find_all('figure', class_="image"):
            for tag2 in tag.find_all('figcaption'):
                new_tag2 = soup.new_tag('span', **{'class': 'figcaption'})
                new_tag2.contents = tag2.contents
                tag2.replace_with(new_tag2)
            new_tag = soup.new_tag('div', **{'class': 'figure'})
            new_tag.contents = tag.contents
            tag.replace_with(new_tag)

        content = content_.prettify()
        return content
