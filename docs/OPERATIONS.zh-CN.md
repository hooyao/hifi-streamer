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
