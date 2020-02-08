# coding=utf-8

import datetime
import os
import sqlite3
import time
from urllib import parse

import requests
from twitter_scraper import get_tweets
from twitterscraper import query_tweets_from_user


class TwitterSpider(object):
    def __init__(self, config, savepath, storepath, database):
        self.config = config
        self.savepath = savepath
        self.storepath = storepath
        self.con = sqlite3.connect(database)

    def __del__(self):
        if self.con:
            self.con.close()

    def start(self):
        try:
            user = self.config['user']
            name = self.config['name']

            if name == '' or name == user:
                name = user

                list_of_tweets = query_tweets_from_user(user, limit=10)
                for tweet in list_of_tweets:
                    if tweet.username == user:
                        name = tweet.fullname
                        break

                cursor = self.con.cursor()
                cursor.execute(
                    'UPDATE twitter_blog SET name=? WHERE user=?', (name, user))
                self.con.commit()

            for tweet in get_tweets(user, pages=1000):
                update_time = int(time.mktime(tweet['time'].timetuple()))  # 时戳
                for photo in tweet['entries']['photos']:
                    self.save_item(photo, name, update_time)
                for video in tweet['entries']['videos']:
                    print('video', video)

                # 更新时间
                new_time = datetime.datetime.fromtimestamp(
                    update_time).strftime("%Y-%m-%d %H:%M:%S")
                cursor = self.con.cursor()
                cursor.execute(
                    'UPDATE twitter_blog SET update_time=? WHERE user=? AND update_time<?', (new_time, user, new_time))
                self.con.commit()
        except Exception as e:
            print('Exception occurs at line ' +
                  e.__traceback__.tb_lineno.__str__(), e)

    def save_item(self, url, subdirectory, update_time):
        r = parse.urlparse(url)
        ts = r.path.split('/')
        file_name = ts.pop()

        file_ext = os.path.join(self.storepath, subdirectory, file_name)
        if os.path.exists(file_ext):
            os.utime(file_ext, (update_time, update_time))
            return

        date = datetime.datetime.fromtimestamp(
            update_time).strftime("%Y-%m-%d")
        file_path = os.path.join(self.savepath, subdirectory, date, file_name)
        if os.path.exists(file_path):
            os.utime(file_path, (update_time, update_time))
            return

        # 超过一定时间的内容，不再爬取
        if self.config['crawl_all'] is False:
            if time.time() - update_time > 3600 * 24 * 3:
                return

        file_dir = os.path.join(self.savepath, subdirectory, date)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        try:
            print("Fetching %s" % (url))
            ir = requests.get(url, timeout=3000)
            if ir.status_code == 200:
                open(file_path, 'wb').write(ir.content)
                os.utime(file_path, (update_time, update_time))
                print("Saved to %s" % (file_path))
        except Exception as e:
            print("Save Failed: %s" % (e))
