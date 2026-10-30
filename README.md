# TIM Android 历史版本

本仓库用于整理 TIM Android 历史版本，提供版本信息、文件校验值和安装包下载入口，方便查找特定版本并核对文件完整性。

## 目录

- `catalog/tim.json`：按版本整理的机器可读索引；
- `checksums/`：版本文件的 SHA-256 校验清单；
- GitHub Releases：各版本 APK 下载页面及安装包。

## 查找版本

打开 [QQ/TIM 版本索引站](https://github.com/luoyul/qq-tim-archive-site)，选择 TIM 后即可查看版本号、文件大小、SHA-256 摘要和对应的 Release。

也可以直接查看 [`catalog/tim.json`](catalog/tim.json)，其中包含版本名称、版本号、文件大小、校验值和 Release 地址。

## 下载与校验

1. 在版本索引中打开目标版本的 Release 页面。
2. 下载页面中的 APK 文件。
3. 使用 SHA-256 工具计算下载文件的摘要，并与 catalog 或 `checksums/` 中的记录进行比较。
4. 摘要一致时，说明下载文件与归档记录相符。

Release tag 使用 `tim-版本名称-版本号` 格式，例如 `tim-4.0.97-4011`。

## 相关仓库

- [QQ Android 历史版本](https://github.com/luoyul/qq-versions)
- [QQ/TIM 版本索引站](https://github.com/luoyul/qq-tim-archive-site)

QQ、TIM 及其安装包的版权归原发布方所有。本仓库仅用于版本信息整理和历史文件查找。
