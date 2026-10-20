# Linux 宿主安装

[English](linux-host.md) | 简体中文

本指南用于准备专用的 systemd Linux 宿主，包括 x86-64 Ubuntu Server。应用安装与资源限制见[运维指南](../OPERATIONS.zh-CN.md)。宿主网络由管理员维护，属于安装前提。

## 架构与服务账号

检查 `uname -m`：`x86_64` 使用 AMD64 镜像，`aarch64` 使用 ARM64 镜像。操作系统镜像也必须兼容 CPU 指令集。标准 Ubuntu Server 包含适合 SSH 维护的工具，minimized 版本可能需要额外安装软件包。

修改网络前验证 SSH 公钥认证。启用 linger、授予音频权限，修改组成员后重新登录。使用 `deploy/preflight.py` 检查 subordinate ID 分配。以服务账号运行应用命令，root 的容器属于另一命名空间。根据目标机器的 DAC 发现结果生成音频服务，不复制其他宿主的声卡编号或服务单元。

## 多网口

安装器可能只为接线网口配置 DHCP。分别检查配置和运行状态：

```sh
ip -br address
networkctl list
sudo netplan get
systemctl cat systemd-networkd-wait-online.service
systemctl --failed
```

对于 Netplan／systemd-networkd 宿主，每个预期使用 DHCP 的网口都需要 `dhcp4: true`；空的 Ethernet 定义不会启用它。保留已有 MAC 匹配、重命名、静态地址、DNS 和路由。网口 MAC 不同，可能取得不同租约；换口后确认 SSH 目标，不把租约写入应用源码或音频服务。

如果任意一个网口联网即可启动，应明确配置该策略。以下示例放在 `/etc/systemd/system/systemd-networkd-wait-online.service.d/90-any-ethernet.conf`；使用宿主实际接口名，并核对可执行文件路径：

```ini
[Service]
ExecStart=
ExecStart=/usr/lib/systemd/systemd-networkd-wait-online --any --ipv4 --interface=enp1s0:routable --interface=enp2s0:routable --timeout=30
```

靠后的 drop-in 会清除之前所有 `ExecStart`，包括 Netplan 生成的同时等待所有接口的命令。它检查可路由的 IPv4，不检查 DNS。将未使用的接口设为 optional 是另一种策略，适合该网口不应阻塞启动的情况。

将网络文件备份到 `/etc/netplan` 以外。用 `netplan generate` 校验 Netplan 改动，在维护期间、有本地控制台回退条件时应用。修改 systemd drop-in 后重新加载 systemd，重启等待服务并检查实际命令和结果。随后验证整机启动及各预期网口的 DHCP。没有地址时，有界等待仍可能失败。禁用 cloud-init 或全部联网等待服务不是未接线网口的通用修复。

## 镜像与认证

四个组件使用同一次成功的合格 CI 发布。写入 `images.json` 前，将包含源码 SHA、运行和尝试次数的标签解析为不可变 registry digest。验证匿名访问、拉取架构及原生 CI 镜像身份。记录更新基线时，使用目标机器实际检查的大小和匹配的 Soloist 有效期。同一源码的定时重建也可能包含不同的 Soloist 二进制，不能混用旧镜像与新元数据。

API key 放在服务账号的私有配置中，权限为 `0600`。通过控制平面输入，或由不打印密钥的脚本仅传输该密钥。不要用复制其他宿主的 Spotify 会话代替配对。有效 API key 可以启动 Soloist，但会话仍可能未登录；需要在 Spotify 中选择新 renderer 完成首次配对。

同一局域网使用不同的 renderer 名称。测试必须命中目标 renderer。`dlna_smoke.py --name` 使用前缀匹配，应选用局域网内唯一前缀。在多 renderer 环境运行其他脚本前，也需检查其发现方式。

## 输出与验收

比较响度前，确认 DAC 的物理输入、输出模式、硬件音量及功放设置，再分别检查 Soloist 会话、Pulse 播放流、选定 sink 和 ALSA 混音器。启动配置为 100% 不能证明所有实时环节的增益。

DLNA 直接输出到 ALSA，设置为 `mixer_type "none"`；其固定数字电平与 PipeWire 输出音量独立。控制器滑块不能通过 DLNA 路径增加软件衰减或改变 DAC 增益。被拒绝的请求与能力声明限制见[固定电平 DLNA](../debugging/troubleshooting.zh-CN.md#固定电平-dlna-与控制器音量请求)。

重启后验证网页访问、实际音量、所选设备健康状态及服务自启动。测试实际安装的 PipeWire／WirePlumber 版本，不从其他宿主推定行为。格式、控制、采样率、持久化和交接见[测试指南](../testing/README.zh-CN.md)。用有界批处理输出检查图采样率：

```sh
pw-top --batch-mode --iterations 3
```

比较选定活动驱动的音频图采样率、解码 PCM 和 USB 输出。监测结果为空属于观测失败。目前 source-rate smoke 在注入合成 PCM 前会暂停真实会话，因此要求 Soloist 已运行并完成配对。

DLNA 格式、合成 PCM、重启和听音检查分别证明不同事项，不能合并代替 Spotify→DLNA→Spotify 交接测试。失败断言或缺失的最终报告在调查清楚前仍是未完成验收，后续人工能播放也不能抹去它们。

生成的报告、私有 URL、设备清单及原始日志不进入版本控制。文档只保留可复现流程与支持边界。
