# AV-Spider 代码优化建议文档

## 1. 代码结构优化

### 1.1 创建基类
创建一个 `BaseSpider` 基类，将两个爬虫类中的重复代码提取到基类中：

```python
class BaseSpider(object):
    def __init__(self, baseUrl, houndUrl):
        self.baseUrl = baseUrl
        self.houndUrl = houndUrl
        # 其他通用初始化代码

    def getHeaders(self):
        # 通用的请求头生成方法

    def request(self, url, tries=1):
        # 通用的请求方法

    def hound(self, data):
        # 通用的数据发送方法

    def printException(self, e):
        # 通用的异常处理方法
```

### 1.2 继承基类
让 `JavBusSpider` 和 `AvmooSpider` 继承 `BaseSpider`，只实现各自特有的逻辑。

## 2. 配置管理优化

### 2.1 创建配置文件
创建 `config.yaml` 文件来管理所有配置项：

```yaml
settings:
  crawl_interval: 3600
  base_url: "http://example.com"
  hound_url: "http://example.com/hound"
  start_url: "http://example.com/start"
  javbus_url: "http://example.com/javbus"
  date_limit: "2023-12-15"
  user_agents:
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3.1 Safari/605.1.15"
    # 更多User-Agent
```

### 2.2 使用配置文件
修改代码以使用配置文件：

```python
import yaml

# 读取配置文件
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
```

## 3. 异常处理优化

### 3.1 完善异常处理
为不同的异常类型提供不同的处理策略：

```python
def request(self, url, tries=1):
    try:
        # 请求代码
        pass
    except requests.exceptions.Timeout:
        # 超时处理
        pass
    except requests.exceptions.ConnectionError:
        # 连接错误处理
        pass
    except Exception as e:
        # 其他异常处理
        pass
```

### 3.2 实现重试队列
对于失败的请求，将其添加到重试队列中：

```python
from queue import Queue

class BaseSpider(object):
    def __init__(self):
        self.retry_queue = Queue()
    
    def add_to_retry_queue(self, url):
        self.retry_queue.put(url)
```

## 4. 安全性增强

### 4.1 实现代理池
使用代理池来避免IP被封禁：

```python
class ProxyPool:
    def __init__(self):
        self.proxies = []
    
    def get_proxy(self):
        # 获取代理
        pass
    
    def update_proxies(self):
        # 更新代理列表
        pass
```

### 4.2 添加请求频率控制
实现请求频率控制，避免对目标网站造成过大压力：

```python
import time
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = Lock()
    
    def acquire(self):
        with self.lock:
            now = time.time()
            # 清理过期请求记录
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            else:
                return False
```

## 5. 性能优化

### 5.1 动态线程池
根据系统资源动态调整线程数：

```python
import multiprocessing

# 根据CPU核心数确定线程数
thread_count = min(10, multiprocessing.cpu_count() * 2)
pool = Pool(processes=thread_count)
```

### 5.2 智能延时机制
根据网站响应情况动态调整请求间隔：

```python
class SmartDelay:
    def __init__(self):
        self.base_delay = 1
        self.current_delay = 1
    
    def adjust_delay(self, response_time, status_code):
        if status_code == 429:  # Too Many Requests
            self.current_delay *= 2
        elif response_time > 5:  # 响应时间过长
            self.current_delay *= 1.5
        elif self.current_delay > self.base_delay:
            self.current_delay *= 0.9
        
        time.sleep(self.current_delay)
```

## 6. 日志系统改进

### 6.1 使用logging模块
替换print语句，使用logging模块：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spider.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 使用日志
logger.info("Spider starts at %s", start_time)
logger.error("Exception occurs at line %s: %s", e.__traceback__.tb_lineno, e)
```

## 7. 数据处理优化

### 7.1 移除硬编码日期
将硬编码的日期移到配置文件中：

```python
# 从配置文件读取日期限制
date_limit = config.get('settings', 'date_limit')
if date_limit:
    date2 = datetime.strptime(date_limit, "%Y-%m-%d")
else:
    # 如果没有配置日期限制，则不进行日期过滤
    next = True
```

### 7.2 添加数据验证
在处理数据前进行验证：

```python
def validate_movie_data(movie):
    required_fields = ['id', 'title', 'poster']
    for field in required_fields:
        if not movie.get(field):
            return False
    return True
```

## 8. 测试完善

### 8.1 添加单元测试
为关键功能编写单元测试：

```python
import unittest
from spider import JavBusSpider, AvmooSpider

class TestSpiders(unittest.TestCase):
    def test_parse_movie(self):
        # 测试电影解析功能
        pass
    
    def test_get_headers(self):
        # 测试请求头生成
        pass

if __name__ == '__main__':
    unittest.main()
```

### 8.2 添加模拟测试
使用模拟库避免对实际网站的请求：

```python
from unittest.mock import patch, Mock

@patch('spider.requests.get')
def test_request_success(mock_get):
    # 模拟成功的请求
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"<html></html>"
    
    # 测试代码
    spider = JavBusSpider("base", "hound", "start")
    result = spider.request("http://example.com")
    
    self.assertEqual(result.status_code, 200)
```

## 9. 文档完善

### 9.1 添加代码注释
为关键函数和复杂逻辑添加详细注释：

```python
def parseList(self, url):
    """
    解析影片列表页面
    
    Args:
        url (str): 列表页面URL
        
    Returns:
        None
        
    该方法会:
    1. 发送请求获取页面内容
    2. 解析影片链接
    3. 过滤已存在的影片
    4. 使用多线程解析影片详情
    5. 处理分页
    """
    # 实现代码
```

### 9.2 编写使用文档
创建 README.md 文件，说明如何配置和运行爬虫：

```markdown
# AV-Spider 使用说明

## 配置
1. 复制 `config.demo.yaml` 为 `config.yaml`
2. 根据需要修改配置项

## 运行
```bash
python main.py
```

## 配置项说明
- crawl_interval: 爬取间隔（秒）
- base_url: 基础URL
- ...
```