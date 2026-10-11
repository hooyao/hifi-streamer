# Design

[English](design.md) | 简体中文

## Context

参见 proposal.md 和架构/音源契约。目标为带 Python 3.11、rootless Podman 和 USB 音频的 systemd Linux 宿主。

## Goals / Non-Goals

**Goals:** 可复现的行为、故障隔离与明确的验收边界。

**Non-Goals:** 尚未实现的流媒体服务、任意硬件认证和未经验证的 bit-perfect 声明。

## Decisions

使用最小运行依赖和多阶段构建。解压镜像门禁为 MPD 200MiB、upmpdcli 160MiB、Soloist 180MiB、web 40MiB。agent 日志限制 1MiB×3、容器日志 2MiB、journal 32MiB、缓存 128MiB。更新使用不可变 registry digest 或已验证本地 image ID。检查空闲输出、磁盘、数据兼容和回滚有效期；串行更新，失败恢复服务与元数据。CI 镜像内容尺寸与设备 inspect 存储尺寸是不同指标。

已验证 libcurl 运行时的 MPD HTTP 接收缓冲为 16KiB。隐式单文件缓存限制为 16MiB，与 128MiB 容器预算独立。CI 使用大虚拟 WAV 和同步 null 输出拒绝持续 HTTP 匿名内存增长。

## Risks / Trade-offs

外部认证和物理音频行为需要手动验收。网络或镜像仓库失败必须可见，不能计为发布成功。硬件健康检查不能代替听音测试。

## Migration Plan

部署前运行自动检查。保留配置、会话数据和可用的回滚镜像。故障时恢复受影响服务，无需重装宿主。
