# MPD内存预算

[English](mpd-memory.md) | 简体中文

## 容器限额

部署生成器通过 `podman run --memory=128m` 为MPD分配128MiB cgroup限额。这是项目预算，不是MPD或Podman默认值，必须按实际输入/解码负载验证。只提高限额不能修复持续增长。

Cgroup包含匿名分配、映射库、缓存及其他计费页面。应对照 `/proc/<pid>/status`、smaps_rollup与cgroup计数，不把容器统计直接当作堆内存。

## HTTP输入

MPD0.24.5将libcurl接收缓冲从16KiB提高到512KiB。在已验证的libcurl8.14.1及反复接收暂停/恢复条件下，大HTTP WAV输入出现持有内存增长；同内容本地文件匿名内存稳定。停止/清空HTTP输入后，相关分配释放。

最小libcurl程序在512KiB接收缓冲下复现增长，16KiB下稳定。这定位到接收/暂停参数组合，不代表已证明所有libcurl版本的具体内部缺陷。

`images/mpd/bounded-input.patch` 恢复16KiB接收缓冲。CI通过同步null输出和虚拟大HTTP WAV，在发布前拒绝持续匿名内存增长。

## 隐式文件缓存

另一个独立行为是上游MPD自动缓存不超过128MiB的可定位HTTP文件。128MiB缓存再加进程/解码开销不能安全放进128MiB容器。补丁将隐式缓存限制为16MiB，大文件使用底层可定位流；配置的解码音频缓冲仍为4MiB，未启用可选队列预取input cache。

## 复现

`tests/mpd_memory_probe.py` 对照同内容7200秒稀疏/虚拟WAV的本地与HTTP路径。临时隔离其他控制器、记录RSS分类、清理播放和样本，报告保存到忽略的输出目录。

```sh
python3 tests/mpd_memory_probe.py --case http --seconds 180 --report .local-build/http.json
python3 tests/mpd_memory_probe.py --case local --seconds 180 --report .local-build/local.json
python3 tests/mpd_memory_ci.py <image> --engine podman
```

回归期间保持128MiB限额，要求内存增长有界并完成长时间验收；短时间稳定不代表两小时负载通过。

补丁镜像在设备上180秒大HTTP/ALSA测试中，所有样本匿名RSS保持7876KiB，总RSS保持25428KiB。原生ARM64 CI同步null测试匿名RSS保持7220KiB，旧镜像超过增长门禁。这些短测验证了针对性修正，长时间发布验收仍独立进行。

## 重启恢复

内存预防与故障恢复是独立要求。MPD用户服务配置 `Restart=on-failure`，延迟五秒重启；OOM退出属于失败。60秒内三次失败会触发systemd启动限流，持续崩溃应保持可见。修正原因后执行 `systemctl --user reset-failed hifi-mpd` 和 `systemctl --user start hifi-mpd`。

MPD通过 `restore_paused "yes"` 恢复队列并保持暂停，不自动恢复声音。启动时显式启用standby输出，使崩溃前禁用过ALSA直出时，控制器的Play仍可被观察。Agent随后通过正常仲裁取得DAC并启用直出。网络来源URI过期时，控制器需要重新发送可用URI。

在空闲且已配置的宿主运行 `python3 tests/mpd_restart_smoke.py --card <runtime-card> --report .local-build/mpd-restart.json`。测试覆盖主动重启、SIGKILL后自动重启、禁用直出时重启。每项都要求暂停恢复，随后DLNA能输出44.1/96kHz、进度前进且无MPD输出错误。SIGKILL验证突然退出的恢复路径，不注入真实cgroup OOM，也不证明听感质量。已验证ARM测试环境三项均通过，自动恢复约需八秒。
