# Proposal

[English](proposal.md) | 简体中文

## Why

Soloist 应作为可选音源与必备 DLNA 共用 DAC，确保将来可增加第三种音源。

## What Changes

- Soloist 容器、专用适配器及本地 WebSocket 状态。
- 基于 owner ID 的串行输出交接、故障静音和热插拔恢复。
- 可选 Spotify 故障不影响 DLNA，增添第三音源假适配器测试。

## Capabilities

### New Capabilities

- `source-arbitration`: Soloist 应作为可选音源与必备 DLNA 共用 DAC，确保将来可增加第三种音源。

### Modified Capabilities

无，当前没有已发布规格。

## Impact

影响modules、images、deploy、tests与维护文档。自动测试配合硬件验收，尚未验证的任务保持未完成。
