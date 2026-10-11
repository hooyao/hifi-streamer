# 音源模块契约

[English](SOURCE-MODULES.md) | 简体中文

## 范围

DLNA为必备音源，Spotify为可选Soloist适配器。Roon、Apple Music和Amazon Music是未来候选，取决于Linux实现、认证、分发条款和资源需求。

音源是逻辑模块，不一定对应单个容器。DLNA包含upmpdcli与MPD，Spotify使用Soloist。通用设备控制应独立于服务专用命令。

## 当前契约

`modules/sources/*/module.json` 声明稳定ID、interface_version、required、adapter、输出路径、控制能力和组件。Registry验证接口兼容性并要求DLNA存在。

适配器提供instance ID、snapshot、release和acquire。快照区分运行、认证、本机active会话、播放与健康状态。无法访问时上报unknown播放状态，不假装已经停止。

恢复会关闭旧控制传输并更新适配器实例 ID，再返回暂停就绪。硬件可用性和实际输出健康独立于播放器快照，参阅[自动恢复](../debugging/audio-recovery.zh-CN.md)。

仲裁器使用source ID、instance ID及序号，拒绝旧/重复请求，串行交接，确认硬件释放后才授予输出权；这不会向容器开放任意设备权限。

MPD的direct/null控制属于DLNA适配器；Soloist WebSocket命令属于Spotify适配器；PipeWire流路由属于输出基础设施。

## 扩展要求

1. 确认可用Linux实现，区分远端接收端与本机客户端。
2. 新增适配器，声明控制能力和输出路径。
3. 即使上游不能pause，也要提供可验证的暂停/停止/释放机制。
4. 声明有界依赖、网络端口、秘密、数据与缓存。
5. 定义版本、有效期、数据迁移和回滚行为。
6. 运行通用仲裁、硬件交接及完整DLNA回归。

新增内置音源目前需要注册适配器factory和配置schema，尚未实现任意第三方插件加载。不支持的控制能力要明确表达，不能伪装成功。

## 兼容性标准

可选音源故障期间DLNA发现和控制仍应可用；控制器看到真实播放/音量能力。备用输出不能静默消耗整首曲目。

验证URL可达、play/pause/stop/seek、队列衔接、重复Play、支持的PCM采样率、FLAC及逐设备DoP。还应覆盖拔插、网络超时、重启和长时间播放。无缝、Native DSD及其他格式需要明确验收场景。
