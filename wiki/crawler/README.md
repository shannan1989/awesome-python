# 爬虫模块

## 概述

`crawler/` 存放面向不同站点的数据采集脚本。本 Wiki 覆盖的 AV 爬虫与排球新闻爬虫独立运行，通过 `shutils.settings` 读取运行配置，并将采集结果提交到由 `hound_url` 指定的接收端。

本文档目录当前只维护 AV 爬虫与排球新闻爬虫；`crawler/` 中的其他脚本不在本 Wiki 的维护范围内。

## 模块索引

| 模块 | 职责 | 文档 |
| --- | --- | --- |
| AV 爬虫 | 采集影片、演员及分类关联数据 | [av-spider.md](./av-spider.md) |
| 排球新闻爬虫 | 采集多个排球资讯站点的新闻 | [volleyball-spider.md](./volleyball-spider.md) |

## 通用运行约定

- `av-spider` 与 `volleyball-spider` 均提供 `compose.yaml`，以容器中的 `python main.py` 启动。
- `config.ini` 为本地运行配置，已被 Git 忽略；文档只描述配置项名称，不记录真实地址或密钥。

## 当前执行模型

| 模块 | 入口 | 调度方式 | 本地输出或下游 |
| --- | --- | --- | --- |
| AV 爬虫 | `crawler/av-spider/main.py` | 顺序执行 AirAv、JavBus，随后按 `crawl_interval` 重启 | 以 HTTP 表单提交影片数据。 |
| 排球新闻爬虫 | `crawler/volleyball-spider/main.py` | 顺序执行 5 个来源，随后按 `crawl_interval` 重启 | 以 HTTP 表单提交新闻数据。 |
