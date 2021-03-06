# coding=utf-8

import sqlite3
import sys

from shutils.settings import Settings

params = sys.argv
params.pop(0)

config = Settings.instance()

database = config.get('settings', 'database')

con = sqlite3.connect(database)
cur = con.cursor()

sql = ('CREATE TABLE IF NOT EXISTS tumblr_blog ('
       'user varchar(64) NOT NULL PRIMARY KEY,'
       "name varchar(64) DEFAULT '',"
       'crawl_all integer DEFAULT 0,'
       'crawl_video integer DEFAULT 0,'
       'crawl_page_size integer DEFAULT 1,'
       'update_time datetime DEFAULT "2000-01-01 00:00:00"'
       ')')
cur.execute(sql)
con.commit()

cur.close()
con.close()
