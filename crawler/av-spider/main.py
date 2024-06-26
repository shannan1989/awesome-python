# coding=utf-8

import time

from shutils import runtime
from shutils.settings import Settings

from spider import AvmooSpider, JavBusSpider

config = Settings.instance()
CrawlInterval = config.getint('settings', 'crawl_interval')
BaseUrl = config.get('settings', 'base_url')
HoundUrl = config.get('settings', 'hound_url')
StartUrl = config.get('settings', 'start_url')
JavBusUrl = config.get('settings', 'javbus_url')

if __name__ == '__main__':
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print('Spider starts at %s' % (start_time))

    start = time.time()

    JavBusSpider(BaseUrl, HoundUrl, JavBusUrl).start()
    AvmooSpider(BaseUrl, HoundUrl, StartUrl).start()

    end = time.time()

    print('Spider finishes, run %s seconds.' % (end - start))

    restart_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end + CrawlInterval))
    print('Spider will restart after %ss, at %s.' % (CrawlInterval, restart_time))

    runtime.restart(delay=CrawlInterval)
