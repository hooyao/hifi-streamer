# Spec Delta

[English](../../../../specs/dlna-rendering/spec.md) | 简体中文

## Purpose

DLNA 是必备音源，必须通过真实发现与协议控制验证，提供采样率保真的网络播放。 本规格定义首版外部可观察行为、故障处理及可复现验收条件，使设备上的自动化检查与后续扩展具有一致依据。

## ADDED Requirements

### Requirement: 常驻 renderer
系统 SHALL 保持 DLNA renderer 在 Spotify 缺失、故障或升级期间可发现与控制。

#### Scenario: Spotify 缺失
- **WHEN** 未配置 Spotify 登录
- **THEN** SSDP 发现及 DLNA 播放成功

### Requirement: 格式保真
系统 SHALL 对支持的 PCM 使用原采样率 ALSA hw 输出并关闭软件音量；DSD SHALL 按验证能力使用 DoP。

#### Scenario: PCM 输出
- **WHEN** 播放 96kHz 测试流
- **THEN** USB 流报告 96kHz

### Requirement: 传输控制
renderer SHALL 接受 URI、play、pause、stop 与支持的 seek，并报告对应状态和位置。

#### Scenario: 暂停后恢复
- **WHEN** 控制器暂停再恢复播放
- **THEN** 状态与输出符合命令

### Requirement: MPD重启恢复
系统 SHALL 在单次异常退出后按有界服务重启规则重新启动MPD，并 SHALL 允许随后控制器播放重新取得DAC直出。恢复的队列 SHALL 保持暂停，直到控制器请求播放。

#### Scenario: MPD突然退出
- **WHEN** DLNA播放期间MPD被强制终止且网络来源仍可用
- **THEN** 服务重新启动，随后控制器播放输出原采样率、进度前进且无MPD输出错误

#### Scenario: 重启前直出已禁用
- **WHEN** MPD重启前直出已被禁用
- **THEN** 随后DLNA Play能通过standby被观察，并由正常仲裁恢复DAC直出
