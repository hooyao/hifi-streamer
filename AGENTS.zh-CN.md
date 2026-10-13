# 仓库指引

[English](AGENTS.md) | 简体中文

HiFi Streamer 是模块化 Linux 网络音频接收端。DLNA 是必备音源；Spotify 是可选适配器。

## 工作指引

模块变更前阅读相关架构和音源契约；贡献流程、验证命令与详细操作见以下指南。

[贡献指南](CONTRIBUTING.zh-CN.md) | [测试](docs/testing/README.zh-CN.md) | [运行与维护](docs/OPERATIONS.zh-CN.md) | [架构](docs/design/AUDIO-ARCHITECTURE.zh-CN.md) | [音源契约](docs/design/SOURCE-MODULES.zh-CN.md)

## 模块索引

| 模块 | 职责 | 源码入口 |
| --- | --- | --- |
| 宿主 agent | 服务生命周期、发现与控制循环 | [程序入口](modules/audio-agent/hifi/__main__.py), [运行循环](modules/audio-agent/hifi/runtime.py), [发现](modules/audio-agent/hifi/devices.py) |
| 输出仲裁 | DAC独占所有权与音频路由 | [仲裁器](modules/audio-agent/hifi/core.py), [PipeWire](modules/audio-agent/hifi/pipewire.py), [采样率](modules/audio-runtime/10-rates.conf) |
| 音源注册 | 内置声明与接口验证 | [注册器](modules/audio-agent/hifi/registry.py), [声明](modules/sources/) |
| DLNA | 必备接收端与ALSA直出 | [声明](modules/sources/dlna/module.json), [适配器](modules/audio-agent/hifi/mpd.py), [MPD镜像](images/mpd/), [upmpdcli镜像](images/upmpdcli/) |
| Spotify | 可选Soloist控制与Pulse输出 | [声明](modules/sources/spotify/module.json), [适配器](modules/audio-agent/hifi/soloist.py), [WebSocket](modules/audio-agent/hifi/websocket.py), [镜像](images/soloist/) |
| 配置与API | 持久化配置、输出音量与设备控制 | [配置](modules/audio-agent/hifi/config.py), [API](modules/audio-agent/hifi/api.py) |
| 网页 | 设备/音源配置与更新控制 | [页面](modules/web/index.html), [代理](modules/web/nginx.conf), [镜像](images/web/) |
| 安装 | 宿主依赖与rootless服务生成 | [宿主准备](deploy/host-setup.sh), [账号预检](deploy/preflight.py), [账号安装](deploy/install.sh), [服务生成器](deploy/manage.py) |
| 更新与维护 | 候选观察、预检与回滚 | [事务](deploy/update.py), [观察](deploy/check-updates.py), [维护](modules/audio-agent/hifi/maintenance.py) |
| CI与验证 | 仓库检查与原生镜像构建 | [工作流](.github/workflows/), [镜像门禁](images/check.py), [测试](tests/) |
| 规格 | 行为变更与验收任务 | [OpenSpec](openspec/) |
