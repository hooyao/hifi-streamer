# Design

[English](design.md) | 简体中文

## Context

参见 proposal.md 和架构/音源契约。目标为带 Python 3.11、rootless Podman 和 USB 音频的 systemd Linux 宿主。

## Goals / Non-Goals

**Goals:** 可复现的行为、故障隔离与明确的验收边界。

**Non-Goals:** 尚未实现的流媒体服务、任意硬件认证和未经验证的 bit-perfect 声明。

## Decisions

在 Alpine 多阶段中构建支持 HTTP、ALSA、PCM/FLAC/MP3/AAC/Vorbis/Opus 和 DSD 的 MPD，避免现成构建的大量可选依赖。upmpdcli 使用发行版包。MPD 直出使用 ALSA hw；null 输出接收交接意图。使用支持 Range 的 HTTP 来源测试 SSDP/SOAP。验证 PCM 44.1/48/96kHz、FLAC、DSD64 DoP，以及长时间播放和控制器兼容性。服务恢复遵循暂停队列与正常输出仲裁。

## Risks / Trade-offs

外部认证和物理音频行为需要手动验收。网络或镜像仓库失败必须可见，不能计为发布成功。硬件健康检查不能代替听音测试。

## Migration Plan

部署前运行自动检查。保留配置、会话数据和可用的回滚镜像。故障时恢复受影响服务，无需重装宿主。
