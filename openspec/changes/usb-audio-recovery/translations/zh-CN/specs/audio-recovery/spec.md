# Spec Delta

[English](../../../../specs/audio-recovery/spec.md) | 简体中文

## Purpose

所选 DAC 或宿主会话故障后恢复可用音频基础设施，提供准确的控制平面错误、独占输出所有权和有界自动修复。

## ADDED Requirements

### Requirement: Missing DAC reporting
控制平面 SHALL 在成功观察确认已配置 DAC 缺失后五秒内报告不可用、撤销输出所有权，并在网页显示可操作错误。播放器/服务存活 SHALL NOT 代表输出就绪。未选择 DAC SHALL 与已配置 DAC 缺失分别报告。

#### Scenario: Configured DAC absent
- **WHEN** 找不到匹配的已配置 DAC
- **THEN** API 报告 `dac_missing`，输出为 disconnected 且无 owner，网页提示检查 DAC 电源和 USB 连接

#### Scenario: Discovery fails
- **WHEN** 无法完成硬件发现
- **THEN** API 报告 `discovery_failed`，硬件可用性为 unknown，不误报缺失或正常

#### Scenario: Partial enumeration
- **WHEN** 匹配 USB 设备存在但没有可用播放端点
- **THEN** API/网页报告 `dac_not_ready`，不显示输出就绪

### Requirement: Stable reconnection
系统 SHALL 按当前设备实例和可用端点协调重新出现的已配置 DAC，即使卡号未变。破坏性恢复前 SHALL 连续三次成功观察且每次至少间隔一秒。恢复期间消失 SHALL 使尝试失效并撤销输出。

#### Scenario: Same card number returns
- **WHEN** DAC 使用旧卡号返回，但设备节点已更新
- **THEN** 恢复就绪前撤销旧映射和旧事件

### Requirement: Bounded staged repair
系统 SHALL 优先使用最小受影响范围修复失败服务和失效路由。恢复 SHALL 使用有限超时、退避和跨设备实例的持久自动重启预算，十分钟最多三次破坏性尝试。耗尽 SHALL 报告 `recovery_exhausted`；限频认证重试 SHALL 允许一次有限尝试。

#### Scenario: Host route missing
- **WHEN** DAC 可用但宿主音频路由持续缺失
- **THEN** 尝试有界会话修复，API 报告恢复进度或失败

#### Scenario: Hardware stays absent
- **WHEN** 已配置 DAC 持续缺失
- **THEN** 报告硬件错误，不反复重启音频栈或宿主

### Requirement: Paused and exclusive restoration
恢复 SHALL 保持暂停和无 owner，保留配置/会话数据及软件音量，只有新的恢复后控制器请求才启用播放。未配置、停用或过期可选音源 SHALL NOT 阻塞 DLNA 就绪。自动修复 SHALL NOT 允许同时访问 DAC。

#### Scenario: Player remains playing on null output
- **WHEN** 播放器在 DAC 缺失时仍报告播放，随后恢复完成
- **THEN** 抑制旧播放意图，直到新控制器请求前保持无声暂停

#### Scenario: Optional source cannot recover
- **WHEN** DLNA 就绪，但 Spotify 认证或二进制过期阻止启动
- **THEN** DLNA 可以播放，Spotify 单独显示可操作错误

### Requirement: Physical route verification
控制平面 SHALL 区分基础设施就绪与实际硬件播放。播放 owner SHALL 在启动宽限后检查所选 DAC 路由和 PCM 运行状态。静音、样本内容变化或正常闲置 sink 挂起 SHALL NOT 单独触发修复。不支持媒体或不可访问 URL SHALL 保持为音源错误。

#### Scenario: Playing source has an unlinked stream
- **WHEN** 音源声称播放，但宽限后连续观察显示没有所选 DAC 路由或运行 PCM
- **THEN** 输出报告 degraded 并调度有界恢复

### Requirement: Maintenance-safe observable recovery
恢复 SHALL 与配置变更及更新串行执行破坏性操作，取消旧设备代次工作并保持状态查询响应。API/网页 SHALL 提供恢复阶段、原因、次数及重试可用性且不泄露秘密。诊断和尝试历史 SHALL 保持有界。

#### Scenario: Update is running
- **WHEN** 更新持有维护锁时观察到故障
- **THEN** 故障仍可见，修复等待且不更改事务管理的镜像或服务
