# Proposal

[English](proposal.md) | 简体中文

## Why

2GB ARM 设备与 eMMC 容量有限，需要小镜像、远端构建以及严格的日志和缓存上限。

## What Changes

- GitHub Actions 构建 ARM64/AMD64 并发布 GHCR，支持替换 Docker Hub 镜像名。
- 镜像大小门禁、运行资源限额、应用与容器日志轮转。
- 按模块更新、Soloist 过期检测、健康检查及回滚。

## Capabilities

### New Capabilities

- `bounded-runtime`: 2GB ARM 设备与 eMMC 容量有限，需要小镜像、远端构建以及严格的日志和缓存上限。

### Modified Capabilities

无，当前没有已发布规格。

## Impact

影响modules、images、deploy、tests与维护文档。自动测试配合硬件验收，尚未验证的任务保持未完成。
