# 运行与维护

[English](OPERATIONS.md) | 简体中文

## 宿主准备

在systemd Linux上使用专用服务账号。以root安装依赖、授予音频设备权限并启用linger：

```sh
sudo sh deploy/host-setup.sh
sudo usermod -aG audio "$USER"
sudo loginctl enable-linger "$USER"
```

修改组后退出并重新登录。Rootless Podman需要唯一subuid/subgid范围及crun。以服务账号运行：

`install.sh` 会在写入应用文件前预检。当前账号在 `/etc/subuid` 和 `/etc/subgid` 中都必须拥有唯一、连续且至少 65536 个 ID 的范围。重命名用户不一定会同步这些分配；管理员修正前必须核对归属和空闲范围。不要复制其他账号的范围，也不要保留互相重叠的用户名/数字 UID 条目。为最终账号启用 linger，通过该账号的 SSH 登录运行安装器，不要使用 root 或组权限尚未刷新的会话。

```sh
systemctl --user enable --now pipewire pipewire-pulse wireplumber
sh deploy/install.sh
```

## 镜像与初始DAC选择

组件为mpd、upmpdcli、soloist、web。拉取验证过的registry digest，或导入验证过的OCI产物。镜像权限与源码仓库权限独立。

```sh
podman pull ghcr.io/hooyao/hifi-streamer/soloist@sha256:<verified-digest>
```

在 `~/.config/hifi-streamer/images.json` 写入四个不可变引用，值必须是完整registry digest或本地 `sha256:<image-id>`，不能是可变标签。本地部署先标记镜像为 `localhost/hifi-<component>:dev`，再运行 `python3 deploy/manage.py record-images`。

使用成功 main 工作流中验证过的 ARM64 导出时，将四个 `bootstrap-<component>-arm64` 产物下载到对应组件目录并传到宿主。按以下方式导入工作流导出的 Docker archive：

```sh
for component in mpd upmpdcli soloist web; do
    podman load --input "$component/image-arm64.tar.gz" || exit 1
    podman tag "docker.io/library/hifi-$component:test" "localhost/hifi-$component:dev" || exit 1
done
python3 deploy/manage.py record-images
```

导出镜像加载后名称为 `docker.io/library/...`，不是 `localhost/...:test`。四个产物应来自同一个已 review 且成功的构建，架构也必须匹配。公开安装要求 GHCR **包**公开，源码仓库公开不代表镜像公开；匿名 manifest 查询或拉取失败时，先修正权限或使用验证过的导出，再选择硬件。不要把 GitHub token 放入应用配置或命令示例。

验证过的多架构发布引用使用 `<source-sha>-<workflow-run-id>-<run-attempt>`。`stable` 和纯源码 SHA 标签是兼容别名：相同源码的定时重建也可能改变其 digest，包括更新 Soloist 二进制。应解析对应构建发布并固定 digest。导出产物应与同一次工作流的 registry 引用比较，不能拿旧导出与新重建的源码别名比较。功能分支手动构建只发布自己的构建引用，不改变生产别名。

记录镜像后，即使 DAC 未连接，也可先启动网页控制平面：

```sh
python3 deploy/manage.py apply
```

打开 `http://<device-address>:8080`，使用私有配置中生成的管理密码登录，在 DAC 可用后选择设备。尚未选择时报告 `dac_unconfigured`；已选设备缺失时报告 `dac_missing`。选定可用硬件前，音频服务保持停止。网页服务已启用，重启后仍会启动。

也可以通过命令行选择稳定 DAC ID：

```sh
PYTHONPATH=modules/audio-agent python3 - <<'PY'
from pathlib import Path
from hifi.config import Config
from hifi.devices import discover
devices = discover()
for device in devices:
    print(device["id"], device["name"])
with open('/dev/tty') as terminal:
    print("DAC ID: ", end="", flush=True)
    selected = terminal.readline().strip()
Config(Path.home() / ".config/hifi-streamer").update({"dac": selected}, devices)
PY
python3 deploy/manage.py apply
systemctl --user enable --now hifi-web
```

## 网页配置与音量

访问 `http://<device-address>:8080`，从私有 `~/.config/hifi-streamer/admin.json` 读取生成的密码。配置DAC、名称、优先级和音源模式。启用Spotify、填写key后从Spotify app配对。

DLNA直出没有软件混音器；Spotify会话音量和PipeWire sink音量独立。启动音量默认40%，可配置0–100。单位增益使用100%会话和宿主0dB，再由DAC/功放控制实际听音音量。提高软件音量前先降低硬件音量。

先用 `pactl list sinks` 和 `pactl list sink-inputs` 检查各层音量：即使 Spotify 显示 100%，DAC sink 为 40% 仍会额外衰减约 −23.9dB。设置单位增益前先暂停播放并降低 DAC/功放音量。Spotify 启动音量设置不会改变宿主 sink。已选择且可用的 DAC，可用以下命令只修改其 PipeWire sink：

```sh
PYTHONPATH=modules/audio-agent python3 - <<'PY'
from pathlib import Path
from hifi.runtime import Runtime
from hifi.pipewire import run
runtime = Runtime(Path.cwd(), Path.home()/'.config/hifi-streamer')
run('pactl', 'set-sink-volume', runtime.hardware.sink(), '100%')
PY
```

重启或重新枚举后再次检查 100%/0dB。WirePlumber 通常会持久化该节点音量；应用在恢复期间保留增益，不会自动提高已有输出音量。全新 Spotify 安装还需要在手机设备列表首次配对，API key 本身不等于登录会话。硬件缺失时，保护性恢复可能停止播放器；暂停就绪恢复前，设备广播也可能消失。

## 音源采样率

Spotify 跟随 Soloist 解码后提供的 Pulse PCM，不再使用固定 44.1kHz 策略。通过认证 `/api/status` 中的 `sources.spotify.pcm_rate`、`pactl list sink-inputs` 和所选 `/proc/asound/card<runtime-card>/stream0` 核对。默认时钟/备用输出采样率只是基线，不是强制音源采样率。尚无 PCM 时等待；格式冲突或不支持时上报音源错误，不静默使用固定值。播放格式须同时满足 USB 播放能力和宿主当前允许采样率。

如果 Soloist 对所有曲目都提供 44.1kHz PCM，输出仍然是 44.1kHz，因为这是可观察到的解码格式。采样率相等不能证明原文件采样率、bit-perfect 或上游没有处理。运行中格式切换可能短暂中断，但不会改变增益/静音。DLNA 继续使用独立的 ALSA 直出路径。

[Spotify 官方 Soloist 说明](https://developer.spotify.com/blog/2026-08-13-introducing-spotify-soloist)标明无损最高 24-bit/44.1kHz。因此当前 Spotify 无损音乐输出 44.1kHz 是正常结果；宿主动态跟随不会增加上游未提供的 96/192kHz 内容。

## 容量预算

| 资源 | 上限 |
| --- | --- |
| Agent | 96MiB，32 tasks |
| MPD / upmpdcli / Soloist / web | 128 /96 /256 /32MiB |
| 容器进程 | 每容器64 PIDs |
| Agent日志 | 当前1MiB，加2份备份 |
| 容器日志 | k8s-file 2MiB |
| 宿主journal | 持久32MiB、运行时16MiB、单文件4MiB、7天 |
| Soloist缓存 | tmpfs128MiB，二进制缓存目标100MB |
| 诊断 | 200行 /64KiB |
| 镜像门禁 MPD / upmpdcli / Soloist / web | 解压200 /160 /180 /40MiB |

Journal限额影响整个宿主。Podman事件和web访问日志关闭。会话持久化，缓存不持久化。vfs因重复层可能超过最终镜像大小。保留当前/回滚镜像，避免在共享宿主全局prune。

## 更新

```sh
python3 deploy/update.py release.json
```

Soloist与web独立更新；MPD/upmpdcli需要兼容的DLNA组合升级。先在 `<component>-release.json` 保存已验证的当前版本元数据。

Manifest包含component、不可变image、设备inspect的size、data_version=1；Soloist还包含由二进制build时间计算的expires_at。更新要求输出空闲、磁盘充足、数据兼容、回滚镜像未过期，并通过进程锁串行执行。失败恢复原服务和元数据；HTTP/WebSocket健康检查不能替代音频验收。

每日timer读取 `update-channels.json` 中HTTPS channel并保存候选。未配置channel则不联网。网页更新/回滚使用已验证候选。

## 检查

```sh
systemctl --user is-active hifi-agent hifi-mpd hifi-upmpdcli hifi-soloist hifi-web
podman stats --no-stream
journalctl --user -u hifi-agent -n 50 --no-pager
```

不要公开含秘密的原始inspect输出。参阅[排障](debugging/troubleshooting.zh-CN.md)与[测试](testing/README.zh-CN.md)。
