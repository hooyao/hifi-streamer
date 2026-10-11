# Design

[English](design.md) | 简体中文

## Context

参见 proposal.md 和架构/音源契约。目标为带 Python 3.11、rootless Podman 和 USB 音频的 systemd Linux 宿主。

## Goals / Non-Goals

**Goals:** 可复现的行为、故障隔离与明确的验收边界。

**Non-Goals:** 尚未实现的流媒体服务、任意硬件认证和未经验证的 bit-perfect 声明。

## Decisions

使用 Python 3.11 标准库宿主 agent，以及通过私有 Unix socket 代理的静态网页容器。服务命令放在适配器，通过注册器加载内置声明。配置原子持久化，秘密权限为 0600；写入要求登录、Origin 验证与 CSRF。避免大型常驻框架。

## Risks / Trade-offs

外部认证和物理音频行为需要手动验收。网络或镜像仓库失败必须可见，不能计为发布成功。硬件健康检查不能代替听音测试。

## Migration Plan

部署前运行自动检查。保留配置、会话数据和可用的回滚镜像。故障时恢复受影响服务，无需重装宿主。
