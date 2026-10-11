# Spec Delta

[English](../../../../specs/bounded-runtime/spec.md) | 简体中文

## Purpose

2GB ARM 设备与 eMMC 容量有限，需要小镜像、远端构建以及严格的日志和缓存上限。 本规格定义首版外部可观察行为、故障处理及可复现验收条件，使设备上的自动化检查与后续扩展具有一致依据。

## ADDED Requirements

### Requirement: 日志有界
系统 SHALL 限制应用、容器与宿主日志占用，并限定诊断导出大小；运行时间增长不能导致日志无限增长。

#### Scenario: 日志压力
- **WHEN** 持续产生超过日志上限的内容
- **THEN** 旧日志被轮转且占用保持预算内

### Requirement: 远端小镜像
发布流程 SHALL 构建 ARM64/AMD64 镜像、验证启动并执行解压镜像大小门禁。

#### Scenario: 镜像超限
- **WHEN** 构建镜像超过组件预算
- **THEN** CI 拒绝发布

### Requirement: 安全更新
系统 SHALL 按模块预拉取已固定镜像，在空闲且磁盘充足时更新，健康失败回滚到兼容且未过期版本。

#### Scenario: 坏镜像
- **WHEN** 候选版本启动失败
- **THEN** 恢复健康旧版本且 DLNA 可用
