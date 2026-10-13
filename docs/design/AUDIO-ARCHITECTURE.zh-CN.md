# 架构

[English](AUDIO-ARCHITECTURE.md) | 简体中文

## 组件

| 组件 | 部署 | 职责 |
| --- | --- | --- |
| MPD | Rootless Podman | HTTP解码、ALSA PCM/DoP输出 |
| upmpdcli | Rootless Podman | DLNA/OpenHome协议、MPD控制 |
| Soloist | Rootless Podman | Spotify Connect、PipeWire Pulse输出 |
| PipeWire/WirePlumber | 宿主用户服务 | DAC路由与备用输出 |
| audio-agent | 宿主用户服务 | 发现、适配器、配置及串行输出权 |
| Web | Rootless Podman | 静态UI及代理到私有Unix socket |
| 安装器 | 显式root准备 | 依赖、设备权限、journal预算 |

网页容器没有Podman管理socket或任意shell API。

## 音频路径

```text
DLNA -> upmpdcli -> MPD -> ALSA hw -> DAC
Spotify -> Soloist -> PipeWire Pulse -> DAC
Web -> private Unix socket -> audio-agent
```

控制器提供可访问的媒体URL，不要求NAS挂载/本地曲库。MPD解码压缩流，直出关闭ALSA转换和软件混音。DoP逐DAC验证；Native DSD与bit-perfect需要单独证据。

## 发现与交接

USB VID/PID、序列号或物理端口建立身份；ALSA卡号与PipeWire节点在运行时解析。

只有一个音源拥有选定DAC。状态为disconnected、idle、switching、active、error，owner是音源ID。串行交接，撤销旧路径并确认硬件释放后再授予输出权。

DLNA交接将Spotify移到standby、挂起硬件sink、启用MPD直出。Spotify交接暂停MPD、启用null输出、恢复硬件sink。播放意图与输出权不同。

Spotify 输出跟随 Soloist 通过 Pulse 实际提供的 PCM 采样率。支持的格式变化会短暂停放流，只重新设置选定 DAC 节点再恢复，不改变增益/静音，也不强制全局时钟。格式稳定时不会反复重开设备。尚无格式时等待；格式错误、多个采样率冲突或不支持的格式会上报音源错误，不得撤销健康的 DLNA 输出权。直出交接会清除音源持有的节点请求。跟随的是解码 PCM，不能据此确认隐藏的原始文件信息或还原 Soloist 内部已做的转换。

拔出撤销输出权；插回重新生成映射，必要时重建容器，默认保持暂停。

[恢复监督器](../debugging/audio-recovery.zh-CN.md)独立于缓慢播放器控制观察硬件，报告输出错误并按持久重试预算修复服务/路由。部署、更新和恢复共用维护锁，修复期间状态查询保持响应。

## 网络与存储

媒体容器用host网络支持发现；MPD和Soloist控制端点只监听loopback。Web监听8080，当前开发版没有密码／session 认证，匹配的 Origin 与进程级 CSRF token 保护状态修改。宿主输出增益独立于音源启动音量和 ALSA 直出；缓存所选 sink 的观察值，确保音频操作期间状态查询仍可响应。

配置/秘密使用服务账号私有XDG目录，会话数据与有界缓存分开。秘密运行时注入，不进入镜像。

Podman4.3使用明确systemd用户单元，不假定Quadlet。容器使用crun、补充设备组、不可变镜像、只读根目录和资源限额。

镜像由原生ARM64/AMD64 CI runner构建。预算与更新见[运行指南](../OPERATIONS.zh-CN.md)，扩展边界见[音源契约](SOURCE-MODULES.zh-CN.md)。
