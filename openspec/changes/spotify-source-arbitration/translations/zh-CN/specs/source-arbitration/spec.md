# Spec Delta

[English](../../../../specs/source-arbitration/spec.md) | 简体中文

## Purpose

Soloist 应作为可选音源与必备 DLNA 共用 DAC，确保将来可增加第三种音源。 本规格定义首版外部可观察行为、故障处理及可复现验收条件，使设备上的自动化检查与后续扩展具有一致依据。

## ADDED Requirements

### Requirement: 独占交接
系统 SHALL 串行释放旧音源硬件后才授予新音源 DAC；失败 SHALL 撤销授权并静音。

#### Scenario: 释放失败
- **WHEN** 旧音源不能确认释放
- **THEN** 新音源不会获得硬件输出

### Requirement: 可扩展 owner
系统 SHALL 以稳定音源 ID 表达输出 owner，并拒绝过期实例事件。

#### Scenario: 第三音源
- **WHEN** 注册兼容的第三个适配器
- **THEN** 无需修改仲裁流程即可切换

### Requirement: Spotify 可选
系统 SHALL 在 Spotify 未认证、退出或过期时保持 DLNA 可用，并展示具体错误。

#### Scenario: 没有 key
- **WHEN** 启动没有 API key 的设备
- **THEN** DLNA 正常且 Spotify 显示未配置
