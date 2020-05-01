# coding=utf-8

import sqlite3
import time
from multiprocessing import Pool

from shutils import runtime
from shutils.settings import Settings

from spider import TumblrSpider

config = Settings.instance()

SavePath = config.get('settings', 'save_path')
StorePath = config.get('settings', 'store_path')
CrawlInterval = config.getint('settings', 'crawl_interval')
Database = config.get('settings', 'database')


def crawl(config):
    spider = TumblrSpider(config, SavePath, StorePath, Database)
    spider.start()


if __name__ == '__main__':
    print('Spider starts at %s' % (time.strftime("%Y-%m-%d %H:%M:%S")))
    start = time.time()

    try:
        con = sqlite3.connect(Database)
        cur = con.cursor()

        tumblrs = []
        cur.execute(
            'SELECT user,crawl_all,crawl_video,crawl_page_size FROM tumblr_blog ORDER BY update_time DESC')
        for row in cur.fetchall():
            tumblrs.append({
                'user': row[0],
                'crawl_all': bool(row[1]),
                'crawl_video': bool(row[2]),
                'crawl_page_size': int(row[3])
            })

        pool = Pool(processes=5)
        pool.map(crawl, tumblrs)
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
    runtime.restart(delay=CrawlInterval)
