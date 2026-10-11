# Proposal

[English](proposal.md) | 简体中文

## Why

建立统一音源契约与轻量控制入口，使未来音源扩展无需重写 DAC 管理。

## What Changes

- 版本化模块声明、独立适配器和统一快照。
- USB DAC 绑定、配置持久化、登录保护的网页与 API。
- 提供假适配器自动测试，验证失败与状态未知。

## Capabilities

### New Capabilities

- `source-control`: 建立统一音源契约与轻量控制入口，使未来音源扩展无需重写 DAC 管理。

### Modified Capabilities

无，当前没有已发布规格。

## Impact

影响modules、images、deploy、tests与维护文档。自动测试配合硬件验收，尚未验证的任务保持未完成。
