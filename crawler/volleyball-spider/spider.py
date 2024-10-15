import abc
import json
import random
import time

import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")  # 启用无头模式
chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速（某些系统需要）
chrome_options.add_argument("--no-sandbox")  # 禁用沙盒（在某些环境中需要）
driver = webdriver.Chrome(options=chrome_options)

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
    
    def parseHref(self, href, url):
        pr = urlparse(url)
        if href.startswith("//"):
            href = pr.scheme + ':' + href
        elif href.startswith("/"):
            href = pr.scheme + '://' + pr.netloc + href
        return href

    def printException(self, e):
        print('Exception occurs at line %s' %
              (e.__traceback__.tb_lineno.__str__()))
        print(e)

class VolleyballChinaSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.urls = [
            'https://www.volleyballchina.com/NewsInfoCategory?categoryId=520096,520097,520098,520099,534929,543412',
            'https://www.volleyballchina.com/NewsInfoCategory?categoryId=520087,520089,520090,520092,520095,520112,534930,536678,536706'
        ]

    def start(self):
        for url in self.urls:
            self.parse_list(url)
    
    def parse_list(self, url):
        response = requests.get(url, headers=self.getHeaders())
        soup = BeautifulSoup(response.content, "html.parser")

        news = []
        for item in soup.find_all('li', class_='w-list-item'):
            article = {
                'source': 'volleyballchina',
                'title': '',
                'url': '',
                'author': '中国排球协会',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': '2024-10-01'
            }

            title_ = item.select_one('p.w-list-title')
            if title_ is None:
                continue
            article['title'] = title_.text

            link_ = item.select_one('a.w-list-link')
            article['url'] = self.parseHref(link_.get('href'), url)

            desc_ = item.select_one('p.w-list-info')
            article['desc'] = desc_.get_text(strip=True)

            poster_ = item.select_one('div.w-list-pic img')
            if poster_ is not None:
                article['poster'] = self.parseHref(poster_.get('src'), url)
            
            info = self.parse_item(article['url'])

            article['content'] = info['content']
            article['publish_time'] = info['publish_time']
            
            news.append(article)
            if len(news) == 10:
                self.hound({'news': json.dumps(news)})
                news = []
     
            time.sleep(1)
        
        if len(news) > 0:
            self.hound({'news': json.dumps(news)})

    def parse_item(self, url):
        content = ''
        publish_time = ''

        try:
            driver.get(url)

            # 等待某个元素加载完成
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "w-detailcontent")))

            print(url)
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Remove all comments from the HTML string
            for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
                comment.extract()

            content_ = soup.find("div", class_="w-detailcontent")
            if content_ is not None:
                content = content_.prettify()

            publish_time = soup.find('span', class_="w-createtime-date").text + ' ' + soup.find('span', class_="w-createtime-time").text
        except Exception as e:
            self.printException(e)

        return { 'content': content, 'publish_time': publish_time}


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
        
        for blockquote in content_.find_all('blockquote', class_='instagram-media'):
            blockquote.extract()

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

        content = ''
        try:
            content = content_.prettify()
        except Exception as e:
            self.printException(e)
        return content
