# Spec Delta

[English](../../../../specs/source-control/spec.md) | 简体中文

## Purpose

建立统一音源契约与轻量控制入口，使未来音源扩展无需重写 DAC 管理。 本规格定义首版外部可观察行为、故障处理及可复现验收条件，使设备上的自动化检查与后续扩展具有一致依据。

## ADDED Requirements

### Requirement: 模块状态隔离
系统 SHALL 显示每个音源的运行、认证、播放、输出与健康状态；不可达的音源 SHALL 报告 unknown，不能被解释为停止。

#### Scenario: 可选音源不可达
- **WHEN** 查询一个已断线的可选音源
- **THEN** DLNA 状态仍独立可查询，断线音源为 unknown

### Requirement: 配置与权限
系统 SHALL 仅允许已登录用户修改配置，隐藏认证秘密，拒绝未知模块、无效配置及跨站请求。

#### Scenario: 非法配置
- **WHEN** 提交未知 DAC 或音源标识
- **THEN** 返回错误且保留原配置

### Requirement: 稳定 DAC 绑定
系统 SHALL 按 USB 身份绑定 DAC，并在声卡编号改变后重新解析；拔出时 SHALL 停止硬件输出。

#### Scenario: 编号改变
- **WHEN** 相同 USB 设备重新枚举
- **THEN** 绑定仍指向原 DAC
