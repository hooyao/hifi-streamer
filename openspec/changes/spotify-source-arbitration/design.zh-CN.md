# Design

[English](design.md) | 简体中文

## Context

参见 proposal.md 和架构/音源契约。目标为带 Python 3.11、rootless Podman 和 USB 音频的 systemd Linux 宿主。

## Goals / Non-Goals

**Goals:** 可复现的行为、故障隔离与明确的验收边界。

**Non-Goals:** 尚未实现的流媒体服务、任意硬件认证和未经验证的 bit-perfect 声明。

## Decisions

提供 snapshot/release/acquire 操作与稳定实例 ID。服务控制放在适配器，通过锁和代次检查串行管理所有权。通过持久本地 WebSocket 查询 Soloist，避免反复 podman exec。使用 PipeWire standby sink 和显式硬件挂起。无法安全释放时拒绝启用双路输出。未配置 key 不能阻塞 DLNA。

## Risks / Trade-offs

外部认证和物理音频行为需要手动验收。网络或镜像仓库失败必须可见，不能计为发布成功。硬件健康检查不能代替听音测试。

## Migration Plan

部署前运行自动检查。保留配置、会话数据和可用的回滚镜像。故障时恢复受影响服务，无需重装宿主。
