# coding=utf-8

import configparser
import os
import sqlite3
import sys
import time
from multiprocessing import Pool

import requests
from twitter_scraper import get_tweets
from twitterscraper.query import query_tweets_from_user

import init
import utils.os.path
import utils.runtime

config = configparser.ConfigParser()
config.read(os.path.abspath('./config.ini'))

SavePath = config.get('settings', 'save_path')
StorePath = config.get('settings', 'store_path')
CrawlInterval = config.getint('settings', 'crawl_interval')
Database = config.get('settings', 'database')

if __name__ == '__main__':
    print('Spider starts at %s' % (time.strftime("%Y-%m-%d %H:%M:%S")))
    start = time.time()

    # TODO

    end = time.time()
    print('Spider finishes, run %s seconds.' % (end - start))

    restart_time = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(end + CrawlInterval))
    print('Spider will restart after %ss, at %s.' %
          (CrawlInterval, restart_time))
    utils.runtime.restart(delay=CrawlInterval)
