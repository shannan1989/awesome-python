# coding=utf-8

import sqlite3
import sys

from shutils.settings import Settings

params = sys.argv
params.pop(0)

if len(params) < 2:
    exit()

config = Settings.instance()

database = config.get('settings', 'database')

con = sqlite3.connect(database)
cur = con.cursor()

sql = ('CREATE TABLE IF NOT EXISTS twitter_blog ('
       'user varchar(64) NOT NULL PRIMARY KEY,'
       "name varchar(64) DEFAULT '',"
       'crawl_all integer DEFAULT 1,'
       'update_time datetime DEFAULT "2000-01-01 00:00:00"'
       ')')
cur.execute(sql)
con.commit()

try:
    cur.execute(
        'INSERT INTO twitter_blog (user,crawl_all) VALUES(?,?)', params)
    con.commit()
except Exception as e:
    params.reverse()
    cur.execute(
        'UPDATE twitter_blog SET crawl_all=? WHERE user=?', params)
    con.commit()

cur.close()
con.close()
