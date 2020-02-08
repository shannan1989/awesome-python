# coding=utf-8

import configparser
import os
import sqlite3
import time
from multiprocessing import Pool

import init
import utils.runtime
from spider import TwitterSpider

config = configparser.ConfigParser()
config.read(os.path.abspath('./config.ini'))

SavePath = config.get('settings', 'save_path')
StorePath = config.get('settings', 'store_path')
CrawlInterval = config.getint('settings', 'crawl_interval')
Database = config.get('settings', 'database')


def crawl(config):
    spider = TwitterSpider(config, SavePath, StorePath, Database)
    spider.start()


if __name__ == '__main__':
    print('Spider starts at %s' % (time.strftime("%Y-%m-%d %H:%M:%S")))
    start = time.time()

    try:
        con = sqlite3.connect(Database)
        cur = con.cursor()

        twitters = []
        cur.execute(
            'SELECT user,name,crawl_all FROM twitter_blog ORDER BY update_time DESC')
        for row in cur.fetchall():
            twitters.append({
                'user': row[0],
                'name': row[1],
                'crawl_all': bool(row[2])
            })

        pool = Pool(processes=5)
        pool.map(crawl, twitters)
        pool.close()
        pool.join()

    finally:
        if cur:
            cur.close()
        if con:
            con.close()

    end = time.time()
    print('Spider finishes, run %s seconds.' % (end - start))

    restart_time = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(end + CrawlInterval))
    print('Spider will restart after %ss, at %s.' %
          (CrawlInterval, restart_time))
    utils.runtime.restart(delay=CrawlInterval)
