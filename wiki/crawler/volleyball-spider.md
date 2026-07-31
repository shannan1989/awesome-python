# 排球新闻爬虫

## 概述

排球新闻爬虫从多个排球资讯站点抓取新闻列表和正文，清理不需要的页面元素后，将新闻以批次形式提交给接收端。该模块只负责采集与格式化，不负责新闻持久化或去重。

## 业务背景

不同资讯站点的页面结构和发布时间格式并不一致。模块通过站点专属爬虫统一输出新闻字段，使下游接收端能够按来源保存和展示内容。

## 核心概念

| 名称 | 说明 |
| --- | --- |
| 新闻对象 | 提交给接收端的一条新闻，包含来源、标题、正文、发布时间等字段。 |
| `hound_url` | 接收新闻批次的外部服务地址。 |
| 批次 | 爬虫累计一定数量的新闻后，以 `news` 表单字段一次提交的集合。不同来源的批次大小不同。 |
| `crawl_interval` | 本轮抓取结束后，下次运行前的等待秒数。 |

## 运行流程

```mermaid
flowchart TD
    A[读取 config.ini] --> B[依次启动已启用的站点爬虫]
    B --> C[抓取列表页]
    C --> D[抓取详情页并清理正文]
    D --> E[按来源批量 POST 到 hound_url]
    E --> F[等待 crawl_interval]
    F --> G[重新启动进程]
```

`main.py` 当前依次启用以下来源：

| 类 | `source` | 站点 | 启用 | 特殊行为 |
| --- | --- | --- | --- | --- |
| `VolleyballChinaSpider` | `volleyballchina` | 中国排球协会 | 是 | 使用 Selenium 无头 Chrome 获取动态详情页。 |
| `SportsVSpider` | `sportsv` | SportsV | 是 | 最多抓取前 2 页，每条新闻单独提交。 |
| `VolSportsSpider` | `volsports` | Vol Sports | 是 | 最多抓取前 2 页。 |
| `FIVBSpider` | `fivb` | 国际排联 | 是 | 将英文日期规范化为 `YYYY-MM-DD`。 |
| `SportsSinaSpider` | `sports.sina` | 新浪体育 | 是 | 清理声明和广告区域。 |
| `VolleyChinaSpider` | `volleychina` | VolleyChina | 否 | 抓取列表和正文。 |

`VolleyballChinaSpider` 顺序抓取两个硬编码分类列表；`FIVBSpider` 与 `SportsSinaSpider` 当前只抓取入口列表页，没有翻页逻辑。

## 类定义

`VolleyballSpider.request()` 未设置显式超时，仅对超时和连接错误递归重试。初始计数为 `1`，计数达到 `5` 时停止，因此最多发出 4 次请求；`4xx/5xx` 响应和其他请求异常直接返回失败值。`parse_href()` 只补全以 `//` 或 `/` 开头的链接，不处理普通相对路径。每个来源的 `start()`、`parse_list()` 和 `parse_item()` 负责适配本来源的列表、详情及正文清理规则。

### 中国排球协会 WebDriver

`VolleyballChinaSpider.get_driver()` 创建并托管 Chrome WebDriver，退出上下文时会关闭浏览器。Linux ARM64 不受 Selenium Manager 支持，因此容器通过环境变量显式指定 Chromium 与 ChromeDriver；其他环境未设置变量时保留默认驱动发现行为。

WebDriver 使用无头模式，并关闭 GPU、Chrome 沙盒及 `/dev/shm` 依赖。详情页请求使用普通 Windows Chrome User-Agent，避免站点将 Linux 无头 Chromium 识别为受限客户端并返回 `429 Too Many Requests`。

## 新闻数据与接口说明

所有来源均将新闻对象序列化为 JSON 字符串，并以表单 POST 方式发送：

| 项目 | 说明 |
| --- | --- |
| 请求地址 | 配置项 `hound_url` 的值 |
| 请求方法 | `POST` |
| 表单字段 | `news` |
| 字段值 | 新闻对象数组的 JSON 字符串 |

新闻对象的统一字段如下。个别站点无法提供的字段会保留为空字符串。

接收端请求只打印响应内容，不调用 `raise_for_status()` 或依据响应状态重试；因此 HTTP 响应是否表示接收成功由接收端约定，当前爬虫不会验证。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | string | 来源标识。 |
| `title` | string | 新闻标题。 |
| `url` | string | 原文地址。 |
| `author` | string | 作者或默认发布机构。 |
| `desc` | string | 摘要。 |
| `poster` | string | 封面图地址。 |
| `content` | string | 清理后的 HTML 正文。 |
| `publish_time` | string | 来源页面提供的发布时间。 |

当前批次大小由来源实现决定：`SportsVSpider` 每条提交；`VolSportsSpider` 每 5 条提交；`VolleyballChinaSpider`、`FIVBSpider` 和 `SportsSinaSpider` 每 10 条提交。列表结束时，未满批次的剩余新闻也会提交。

示例：

```json
{
  "news": "[{\"source\": \"fivb\", \"title\": \"...\", \"url\": \"https://...\", \"author\": \"国际排联\", \"desc\": \"...\", \"poster\": \"https://...\", \"content\": \"<div>...</div>\", \"publish_time\": \"2026-07-11\"}]"
}
```

## 配置与部署

| 配置项 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `crawl_interval` | integer | 是 | 下一轮任务前的等待秒数。 |
| `hound_url` | string | 是 | 接收新闻的服务地址。 |

各新闻来源 URL 当前硬编码在对应爬虫类中，不能通过 `config.ini` 修改。

容器使用以下环境变量：

| 环境变量 | Docker 默认值 | 说明 |
| --- | --- | --- |
| `CHROME_BIN` | `/usr/bin/chromium` | Chromium 可执行文件路径；未设置时由 Selenium 按默认规则查找浏览器。 |
| `CHROMEDRIVER_BIN` | `/usr/bin/chromedriver` | ChromeDriver 可执行文件路径；未设置时由 Selenium Manager 自动查找或下载驱动。 |

容器基于 `docker.1ms.run/python:3.13-slim`，通过清华镜像安装 Chromium、ChromeDriver 和 Python 依赖。`compose.yaml` 将当前目录挂载到 `/app`，并以 `python main.py` 启动。

## 常见问题

- 中国排球协会来源依赖 Chrome WebDriver；容器镜像已安装 Chromium 和对应驱动。修改 Dockerfile 后需要重新构建镜像，旧镜像不会自动获得浏览器环境。
