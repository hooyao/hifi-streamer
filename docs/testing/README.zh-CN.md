# 测试

[English](README.md) | 简体中文

## 自动检查

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

单元测试覆盖配置校验、凭据隐藏、HTTP认证/CSRF、模块注册、第三音源仲裁、旧事件、释放失败、热插拔状态、WebSocket帧、日志/缓存上限及更新回滚/预检。

## 硬件集成

输出健康状态及有界修复行为见[自动音频恢复](../debugging/audio-recovery.zh-CN.md)。

在已配置宿主上以服务账号运行。测试会改变播放，保持DAC/功放低音量，独占测试期间避免其他控制器操作。

```sh
python3 tests/dlna_smoke.py --card <runtime-card> --dsd --report .local-build/dlna.json
python3 tests/soloist_restart_smoke.py
python3 tests/agent_restart_smoke.py
python3 tests/mpd_restart_smoke.py --card <runtime-card> --report .local-build/mpd-restart.json
python3 tests/recovery_device_smoke.py --fault mpd --automatic-only --report .local-build/recovery.json
python3 tests/spotify_switch_smoke.py --card <runtime-card> --report .local-build/switch.json
sh tests/podman_tmpfs_smoke.sh
```

DLNA smoke验证SSDP、AVTransport URI/play/pause/seek/stop、44.1/48/96kHz WAV/FLAC、下一URI、重复Play和可选DSD64 DoP。USB异步反馈容差0.1%，不是bit-perfect比较。

Spotify测试需要已配对账号，验证输出交接及重启后的启动音量。`host_api_smoke.py` 面向未配置Spotify和DX5 II测试配置，不能当作通用已部署设备健康检查。

Agent 重启 smoke 要求 Spotify 已在播放且硬件时钟请求已设置。验证重启后无 owner 且暂停、清理持久节点时钟、恢复预算不变、拒绝健康状态重试，以及新的 44.1kHz 播放。

MPD重启测试覆盖主动及突然退出、暂停恢复队列和禁用直出状态恢复，要求随后DLNA能输出44.1/96kHz且播放进度前进。恢复边界见[MPD内存与恢复](../debugging/mpd-memory.zh-CN.md)。

恢复故障注入支持 `mpd`、`start-limit`、`player`、`route` 和 `session`。使用 `--automatic-only` 前等待自动预算可用，否则测试失败，不把手动重试计为自动验收。测试会停止服务并要求暂停就绪。启动限流测试在持有维护锁时临时注入启动失败，撤掉覆盖配置后才允许修复。真实拔插/断电和后续播放/听音另行验证。

## 长时间测试

```sh
python3 tests/dlna_soak.py --card <runtime-card> --seconds 7200 --report .local-build/soak.json
```

按需生成静音WAV HTTP流，检查renderer URI、播放位置、USB输出和内存；其他控制器改变URI会使测试失败。只有报告最终status为passed才能计为验收通过。

## 更新集成

`tests/update_device_smoke.py` 使用不兼容的已缓存镜像测试真实web更新器，验证回滚/健康提交及DLNA未重启。要求DAC输出空闲及不可变镜像已存在。

生成报告和原始日志作为本地/CI产物，不跟踪为文档。仓库只保留脱敏且可复现的测试定义与支持边界。

## 手动验收

对目标格式验证LMS Bridge与Audio Station、pause/seek/next及队列行为。验证Spotify听音质量、双向交接、DAC拔插不自动恢复、整机重启。在发布验收产物中记录控制器版本及DAC能力。

协议/USB检查不能证明听音质量，单一测试设备不能认证Native DSD、无缝或所有DAC。

## 硬件配置

参见[M401A验证范围](m401a.zh-CN.md)。CPU频率诊断脚本仅用于该配置，不作为通用安装默认值。
