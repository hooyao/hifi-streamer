# 排障

[English](troubleshooting.md) | 简体中文

## 无声音

分别检查真实播放与路由：

```sh
pactl list short sinks
pactl list short sink-inputs
pw-link -l
cat /proc/asound/card*/stream0
```

UI显示播放不能证明硬件输出。确认选定USB DAC存在、流指向它、sink未挂起。只保留PipeWire Pulse一个音频服务器，不再启动独立PulseAudio daemon。

## 音量低或采样率异常

检查音源会话、sink-input、sink和硬件混音器音量。全新 Soloist initial_volume 和宿主输出默认100%；已有 sink40%仍会额外衰减约23.9dB。控制平面显示实际宿主音量，并明确提示静音或输出不可用。校正增益前降低硬件听音音量。

核对 `pw-metadata -n settings 0` 和allowed-rates配置。44.1kHz流以48kHz输出说明重采样。DSD64 DoP使用176.4kHz传输，不应当作Spotify格式。

应比较解码 PCM、运行中的驱动图和 USB 采样率。`clock.rate` 元数据是默认偏好：即使受支持的驱动图运行在 48000，它也可能仍显示 44100，不能仅凭此诊断转换。使用 `pw-top`/节点协商格式和 USB 反馈核对。出现音源 `rate_error` 时应修正或换支持的格式重试，不要强制 44100 隐藏错误。格式切换先停放流，再关闭/重开选定 sink；活动 Pulse 客户端可能使 DAC 仍被占用。

## DAC忙或缺失

MPD单独重启后必须保留可用standby输出。持久状态可能已关闭direct；若两者都关闭，新DLNA请求会在仲裁看到播放边沿前失败。部署在启动时启用standby，交接到直出时再关闭。

`Device or resource busy` 表示有其他占用者，确认MPD直出和PipeWire没有同时使用DAC。不能只凭软件状态证明释放。

`No such device` 需要重新USB发现。重枚举可能使容器bind mount失效，即使卡号没变。重建映射时保留会话数据。

内核 `cannot set/get freq ... err -71` 表示 USB 协议事务失败，不代表 Spotify 选择了错误音频格式。如果随后出现 `USB disconnect`，且 DAC 从 `lsusb` 中消失，仅重启服务无法恢复内核已不再枚举的设备。检查 DAC 实际供电/输入、线缆、接口和盒子电源；断开无关 USB 存储进行受控对比。必要时给 DAC 完全断电重开，重新枚举确认后再播放。对比成功本身不能证明拔掉的存储或线缆就是根因。不要在音频恢复循环中加入无限控制器重置。

## 爆音和断续

按ALSA独立纯音、PipeWire纯音、服务流依次隔离。相同条件下记录CPU频率、USB错误、路由与调度数据，不同时改变多个变量。

经过验证的M401A/内核配置中，调频CPU PLL错误与断续相关；固定1.2GHz是可用规避方案，见[硬件配置](../testing/m401a.zh-CN.md)。增大缓冲本身不是已确认修复。纯音/采样率检查不能代替听音验收。

## Rootless服务

检查服务账号audio组、subuid/subgid和linger。使用该账号的 `systemctl --user` 和 `podman`；root的容器属于另一命名空间。读取XDG_RUNTIME_DIR，不写死UID。

## Soloist启动与控制

容器内必须具备兼容glibc与运行库。本地真实状态/控制需开启loopback WebSocket。检查版本和build有效期，exit10不能无限重启。

Podman4.3不接受已测tmpfs挂载中的uid/gid参数。缓存使用隔离容器内独立128MiB、mode1777的tmpfs。挂载Pulse socket目录，不挂载失效的单个socket。

## 协议与更新失败

有效 HTTP MP3 同时出现 `cannot seek!`、`mpg123_getformat() failed` 和 `unrecognized file`，可能是解码器回调缺陷，而非文件损坏或 NAS 认证失败。核对 HTTP 200／206、audio/mpeg 和 MPEG 帧头，避免公开临时媒体 URL。修正后的 mpg123 回调支持受限的 SET／CUR／已知 END 定位，并注册 audio/mpeg。需同时验证文件解码和 HTTP 传输；`decoders` 中出现插件并不能证明流兼容性。保留 16MiB 隐式缓存和 128MiB 容器预算。

对照控制器展示的原文件信息与实际传来的容器格式、解码采样率。原始高采样率 FLAC 经过控制器转换后可能成为 44.1kHz MP3，提高 DAC 采样率无法恢复原音源。在归因于解码器之前，先核对 renderer 的协议声明是否改变。合成测试期间停止所有控制器，并将其他播放请求替换夹具 URI 的情况判为无效测试。

Cgroup OOM或HTTP播放内存增长见[MPD内存预算](mpd-memory.zh-CN.md)。

HTTP定位要求音频源支持Range。Renderer能力必须与输出控制一致，不添加close_on_pause等不支持的MPD参数。

更新候选要求不可变引用、兼容元数据、空间充足、输出空闲及有效回滚版本。读取近期有界日志，不公开凭据或完整inspect。
