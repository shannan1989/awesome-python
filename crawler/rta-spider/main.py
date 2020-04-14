# coding=utf-8

import configparser
import os
import time

from shutils import runtime

from spider import RtaSpider

config = configparser.ConfigParser()
config.read(os.path.abspath('./config.ini'))

SavePath = config.get('settings', 'save_path')
StorePath = config.get('settings', 'store_path')
CrawlInterval = config.getint('settings', 'crawl_interval')

if __name__ == '__main__':
    print('Spider starts at %s' % (time.strftime("%Y-%m-%d %H:%M:%S")))
    start = time.time()

    for host in config.options('targets'):
        name = config.get('targets', host)
        RtaSpider('https://' + host, name, SavePath, StorePath).start()

    end = time.time()
    print('Spider finishes, run %s seconds.' % (end - start))

    restart_time = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(end + CrawlInterval))
    print('Spider will restart after %ss, at %s.' %
          (CrawlInterval, restart_time))
    runtime.restart(delay=CrawlInterval)
