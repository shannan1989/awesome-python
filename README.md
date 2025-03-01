# awesome-python

在 Python 项目中，如何管理所使用的全部依赖库呢？

最主流的做法是维护一份 requirements.txt ，记录下所有依赖库的名字及其版本号。

常见的生成 requirements.txt 的方法是:
```
pip freeze > requirements.txt
```
这种方法用起来方便，但有几点不足：

- 它搜索依赖库的范围是全局环境，因此会把项目之外的库加入进来，造成冗余（一般是在虚拟环境 virtualenv 中使用，但还是可能包含无关的依赖库）
- 它只会记录以 pip install 方式安装的库
- 它对依赖库之间的依赖关系不做区分
- 它无法判断版本差异及循环依赖等情况
- …………

## 如何安装全部依赖库
```
pip install -r requirements.txt
```

## 使用pigar
安装
```
pip install pigar
```
使用
```
pigar --without-referenced-comments
```
检查依赖库的最新版本
```
pigar check
```
