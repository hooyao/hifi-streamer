# HiFi Streamer

[English](README.md) | 简体中文

面向低成本 Linux ARM 设备和外置 USB DAC 的模块化网络音频接收端。

HiFi Streamer 通过 upmpdcli 和 MPD 接收 DLNA 音频，通过 Soloist 接收 Spotify Connect 音频。本地 agent 协调单个 DAC 的使用权，网页提供设备选择和音源配置。

## 功能

- 必备 DLNA renderer，使用 ALSA 直出，保留 PCM 源采样率，并按设备能力支持 DSD over PCM（DoP）。
- 可选 Spotify Connect 音源，使用 Soloist 和宿主 PipeWire Pulse 服务。
- 自动音源交接、可配置优先级和固定音源模式。
- USB DAC 身份识别及拔插恢复。
- Rootless Podman 容器、有界日志、资源限额和镜像体积门禁。
- 独立版本的音源适配器，为后续集成提供扩展边界。

## 项目状态

首版实现正在验证，尚未成为经过通用环境认证的生产版本。

硬件覆盖范围见[测试指南](docs/testing/README.zh-CN.md)。无缝播放、Native DSD，以及任意控制器或 DAC 的兼容性尚未认证。Roon、Apple Music、Amazon Music 尚未实现。

## 环境要求

- 带 systemd 的 Linux、Python 3.11 或更高版本，以及支持音频的 USB DAC。
- Podman 4.3 或更高版本、crun 和 rootless 用户命名空间。
- PipeWire、pipewire-pulse、WirePlumber。
- 具有音频设备访问权限并启用 systemd linger 的专用服务账号。
- 允许 DLNA 发现，并能访问控制器提供的音频 URL 的局域网。
- Spotify 播放需要 Soloist API key 和兼容的 Spotify 账号。

GitHub Actions 构建 ARM64 和 AMD64 镜像。当前硬件验证覆盖 [M401A 配置](docs/testing/m401a.zh-CN.md)。

## 快速开始

在目标主机克隆仓库：

```sh
git clone https://github.com/hooyao/hifi-streamer.git
cd hifi-streamer
sudo sh deploy/host-setup.sh
```

继续按[安装与配置指南](docs/OPERATIONS.zh-CN.md)准备服务账号、载入不可变镜像、选择 DAC 并启动服务。安装前必须验证镜像仓库访问；成功构建的 OCI 导出产物也可用于初始部署。

部署后访问 `http://<device-address>:8080`，使用设备生成的管理密码，配置 DAC。有 API key 后再启用 Spotify。音源与 DAC 都可能影响音量，听音前应核对两者。

## 音频路径

```text
DLNA controller -> upmpdcli -> MPD -> ALSA -> USB DAC
Spotify app     -> Soloist -> PipeWire    -> USB DAC
Web UI          -> audio-agent -> source adapters and DAC arbitration
```

MPD 负责解码压缩音频。DoP 在 PCM 帧中传输 DSD；配置和采样率检查本身都不能证明 bit-perfect。

## 测试

在 Linux 上运行不依赖第三方库的单元测试：

```sh
python3 -m unittest discover -s tests -v
```

硬件测试会改变播放状态。DLNA、音源交接、重启、热插拔和长时间测试见[测试指南](docs/testing/README.zh-CN.md)。

## 文档

- [运行与维护](docs/OPERATIONS.zh-CN.md)
- [架构](docs/design/AUDIO-ARCHITECTURE.zh-CN.md)
- [音源模块契约](docs/design/SOURCE-MODULES.zh-CN.md)
- [排障](docs/debugging/troubleshooting.zh-CN.md)
- [测试](docs/testing/README.zh-CN.md)

## 贡献

使用 OpenSpec 描述行为、实现决策及可验证的验收条件。proposal、规格、实现和 review 流程见[贡献指南](CONTRIBUTING.zh-CN.md)。

代码注释与 docstring 使用英文。产品及贡献文档提供英文和简体中文两版，并包含双向语言切换链接。OpenSpec 内容全部只用英文。

## 许可证

项目许可证尚未选定。依赖及随附二进制继续遵循各自的上游许可证。
