import abc
import json
import logging
import random
import time
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment
from requests.exceptions import Timeout, ConnectionError, RequestException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


def remove_tags(soup, tags):
    for tag in soup.find_all(tags):
        tag.decompose()
    return soup

def remove_attrs(soup, attrs):
    attrs_set = set(attrs)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in attrs_set:
                del tag[attr]
    return soup


class VolleyballSpider(metaclass=abc.ABCMeta):
    houndUrl = ''

    @abc.abstractmethod
    def start(self):
        pass

    def hound(self, data):
        try:
            r = requests.post(self.houndUrl, data, headers=self.get_headers())
            print(r.content)
        except Exception as e:
            self.print_exception(e)

    def get_headers(self) -> dict:
        """获取请求头"""
        userAgents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edge/18.17763'
        ]
        headers = {
            'User-Agent': random.choice(userAgents)
        }
        return headers
    
    def parse_href(self, href: str, url: str) -> str:
        """
        解析相对链接为绝对链接
        
        Args:
            href (str): 原始链接，可能是相对链接
            url (str): 当前页面的完整URL
            
        Returns:
            str: 转换后的绝对链接
        """
        pr = urlparse(url)
        if href.startswith("//"):
            href = pr.scheme + ':' + href
        elif href.startswith("/"):
            href = pr.scheme + '://' + pr.netloc + href
        return href

    def print_exception(self, e):
        print('Exception occurs at line %s' % (e.__traceback__.tb_lineno.__str__()))
        print(e)

    def request(self, url: str, tries: int =1, max_retries: int =5):
        """发送HTTP请求"""
        if tries >= max_retries:
            logging.error(f"Max retries exceeded for {url}")
            return False
        try:
            r = requests.get(url, headers=self.get_headers())
            r.raise_for_status()
            print('%s %s' % (r.status_code, url))
            if r.status_code != 200:
                time.sleep(5)
                return self.request(url, tries + 1, max_retries)

            return r
        except (Timeout, ConnectionError) as e:
            logging.warning(f"请求超时/连接错误 {url}: {e}")
            time.sleep(5)
            return self.request(url, tries + 1, max_retries)
        except RequestException as e:
            logging.error(f"请求错误 {url}: {e}")
            return False
        except Exception as e:
            logging.error(f"未知错误 {url}: {e}")
            return False


class SportsSinaSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.url = 'https://sports.sina.com.cn/others/volley.shtml'

    def start(self):
        self.parse_list(self.url)
    
    def parse_list(self, url):
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")

        uls = soup.find_all('ul', class_='list2')

        news = []
        for item in uls[1].find_all('li'):
            article = {
                'source': 'sports.sina',
                'title': '',
                'url': '',
                'author': '新浪体育',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': ''
            }

            title_ = item.select_one('a')
            if title_ is None:
                continue
            article['url'] = title_.get('href')
            article['title'] = title_.text
            
            info = self.parse_item(article['url'])

            article['content'] = info['content']
            article['publish_time'] = info['publish_time']
            article['poster'] = info['poster']

            news.append(article)
            if len(news) == 10:
                self.hound({'news': json.dumps(news)})
                news = []

            time.sleep(1)

        if len(news) > 0:
            self.hound({'news': json.dumps(news)})

    def parse_item(self, url):
        r = self.request(url)
        if r == False:
            return
        
        content = ''
        publish_time = ''
        poster = ''

        soup = BeautifulSoup(r.content, "html.parser")
        soup = remove_attrs(soup, ['data-sudaclick', 'data-link'])

        # Remove all comments from the HTML string
        for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
            comment.extract()
        
        for tag in soup.find_all('div', class_='show_statement'):
            tag.decompose()
        for tag in soup.find_all('div', id='left_hzh_ad'):
            tag.decompose()

        content_ = soup.find("div", class_="article")
        content = content_.prettify()

        imgs = content_.find_all('img')
        if len(imgs) > 0:
            poster = self.parse_href(imgs[0].get('src'), url)

        publish_time = soup.find('span', class_='date').text
        publish_time = publish_time.replace('年', '-').replace('月', '-').replace('日', '')

        return { 'content': content, 'publish_time': publish_time, 'poster': poster }


class VolleyballChinaSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.urls = [
            'https://www.volleyballchina.com/NewsInfoCategory?categoryId=520097,520098',
            'https://www.volleyballchina.com/NewsInfoCategory?categoryId=520089,520090,520092,520095,534930,536678,536706'
        ]

    @contextmanager
    def get_driver(self):
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 启用无头模式
            chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速（某些系统需要）
            chrome_options.add_argument("--no-sandbox")  # 禁用沙盒（在某些环境中需要）
            chrome_options.add_argument("--disable-dev-shm-usage") # 禁用 /dev/shm 依赖，避免空间不足
            driver = webdriver.Chrome(options=chrome_options)
            yield driver
        except Exception as e:
            logging.error(f"Error initializing WebDriver: {e}")
            raise
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logging.error(f"Error closing WebDriver: {e}")

    def start(self):
        for url in self.urls:
            self.parse_list(url)
    
    def parse_list(self, url):
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")

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
                'publish_time': ''
            }

            title_ = item.select_one('p.w-list-title')
            if title_ is None:
                continue
            article['title'] = title_.text

            link_ = item.select_one('a.w-list-link')
            article['url'] = self.parse_href(link_.get('href'), url)

            desc_ = item.select_one('p.w-list-info')
            article['desc'] = desc_.get_text(strip=True)

            poster_ = item.select_one('div.w-list-pic img')
            if poster_ is not None:
                article['poster'] = self.parse_href(poster_.get('src'), url)
            
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
            with self.get_driver() as driver:
                driver.get(url)
                # 等待某个元素加载完成
                WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "w-detailcontent")))

                print(url)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                soup = remove_attrs(soup, ['id', 'longdesc', 'data-link', 'data-original', 'data-user-action', 'data-user-action-time'])

                # Remove all comments from the HTML string
                for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
                    comment.extract()

                content_ = soup.find("div", class_="w-detailcontent")
                if content_ is not None:
                    content = content_.prettify()

                publish_time = soup.find('span', class_="w-createtime-date").text + ' ' + soup.find('span', class_="w-createtime-time").text
        except Exception as e:
            self.print_exception(e)

        return { 'content': content, 'publish_time': publish_time }


class VolleyChinaSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.url = "http://www.volleychina.org/allnews/index.html"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url):
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")

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
                a.decompose()
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
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")

        # Remove all comments from the HTML string
        for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
            comment.extract()

        content = soup.find("div", class_="detail-context").prettify()
        return content


class VolSportsSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.url = "https://volsports.co/blog/category/news/"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url):
        r = self.request(url)
        if r == False:
            return
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
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")
        soup = remove_tags(soup, ['iframe', 'script'])
        soup = remove_attrs(soup, ['id', 'srcset', 'sizes', 'aria-describedby', 'data-recalc-dims'])

        content_ = soup.find("div", class_="post-content")
        
        for blockquote in content_.find_all('blockquote', class_='instagram-media'):
            blockquote.decompose()

        # 删除每个h标签及其后面的内容
        for h in content_.find_all(['h2', 'h3']):
            if h.text.find('延伸閱讀') == -1:
                continue
            for tag in h.find_next_siblings():
                if tag.name == h.name:
                    break
                tag.decompose()
            h.decompose()

        content = content_.prettify()
        return content


class SportsVSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.url = "https://www.sportsv.net/volleyball"

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url, current_page=1):
        r = self.request(url)
        if r == False:
            return
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

            title_ = item.select_one('h3 a')
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
        r = self.request(url)
        if r == False:
            return
        soup = BeautifulSoup(r.content, "html.parser")
        soup = remove_tags(soup, ['iframe', 'script'])
        soup = remove_attrs(soup, ['id', 'srcset', 'data-bucket-id', 'data-height', 'data-width'])

        content_ = soup.find("div", class_="article-content")

        for tag in content_.find_all('div', class_='adv-article-content'):
            tag.decompose()

        for tag in content_.find_all('figure', class_="image"):
            for tag2 in tag.find_all('figcaption'):
                new_tag2 = soup.new_tag('span', **{'class': 'figcaption'})
                for child in tag2.contents:
                    new_tag2.append(child)
                tag2.replace_with(new_tag2)
            new_tag = soup.new_tag('div', **{'class': 'figure'})
            for child in tag.contents:
                new_tag.append(child)
            tag.replace_with(new_tag)

        content = ''
        try:
            content = content_.prettify()
        except Exception as e:
            self.print_exception(e)
        return content


class FIVBSpider(VolleyballSpider):
    def __init__(self):
        super().__init__()
        self.url = 'https://www.fivb.com/category/volley/'

    def start(self):
        self.parse_list(self.url)

    def parse_list(self, url):
        r = self.request(url)
        if r == False :
            return
        soup = BeautifulSoup(r.content, "html.parser")

        items = soup.find_all('article', class_='mod-article-item')

        news = []
        for item in items:
            article = {
                'source': 'fivb',
                'title': '',
                'url': '',
                'author': '国际排联',
                'desc': '',
                'poster': '',
                'content': '',
                'publish_time': ''
            }

            article['url'] = item.select_one('a').get('href')

            info = self.parse_item(article['url'])

            article['title'] = info['title']
            article['desc'] = info['desc']
            article['content'] = info['content']
            article['publish_time'] = info['publish_time']
            article['poster'] = info['poster']

            news.append(article)
            if len(news) == 10:
                self.hound({'news': json.dumps(news)})
                news = []

            time.sleep(1)

        if len(news) > 0:
            self.hound({'news': json.dumps(news)})

    def parse_item(self, url):
        r = self.request(url)
        if r == False :
            return

        title = ''
        desc = ''
        content = ''
        publish_time = ''
        poster = ''

        soup = BeautifulSoup(r.content, "html.parser")
        soup = remove_tags(soup, ['iframe', 'script'])
        soup = remove_attrs(soup, ['srcset'])

        # Remove all comments from the HTML string
        for comment in soup.find_all(string=lambda string: isinstance(string, Comment)):
            comment.extract()

        main = soup.find('div', class_='single-new')

        title_ = main.find('div', class_='title-wrapper')

        title = title_.select_one('h1').text.strip()
        desc = title_.select_one('h2').text.strip()

        meta = main.find('div', class_='meta position-relative')

        cover = meta.select_one('img', class_='cover')
        poster = self.parse_href(cover.get('src'), url)

        publish_time_ = meta.find('div', class_='date').text.strip()
        publish_time = datetime.strptime(publish_time_, "%b %d, %Y").strftime("%Y-%m-%d")

        content_ = main.find('article', class_='post').find('div', class_='container').find('div', class_='row')

        for blockquote in content_.find_all('blockquote', class_='instagram-media'):
            blockquote.decompose()
        
        for div in content_.find_all('div', class_='spacer-3'):
            div.decompose()

        for figure in content_.find_all('figure'):
            for figcaption in figure.find_all('figcaption'):
                span = soup.new_tag('span', **{'class': 'figcaption'})
                for child in figcaption.contents:
                    span.append(child)
                figcaption.replace_with(span)
            div = soup.new_tag('div', **{'class': 'figure'})
            for child in figure.contents:
                div.append(child)
            figure.replace_with(div)

        content = content_.prettify().replace('\n', '')

        return { 'title': title, 'desc': desc, 'content': content, 'publish_time': publish_time, 'poster': poster }
