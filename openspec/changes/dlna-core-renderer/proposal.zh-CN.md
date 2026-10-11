# Proposal

[English](proposal.md) | 简体中文

## Why

DLNA 是必备音源，必须通过真实发现与协议控制验证，提供采样率保真的网络播放。

## What Changes

- 独立 MPD 与 upmpdcli 容器，host 网络发现、回环 MPD 控制。
- ALSA hw 直出、DoP、无软件混音，支持播放控制及下一首。
- 自动 SSDP、SOAP、HTTP 音频和实际 USB 流检查。

## Capabilities

### New Capabilities

- `dlna-rendering`: DLNA 是必备音源，必须通过真实发现与协议控制验证，提供采样率保真的网络播放。

### Modified Capabilities

无，当前没有已发布规格。

## Impact

影响modules、images、deploy、tests与维护文档。自动测试配合硬件验收，尚未验证的任务保持未完成。
