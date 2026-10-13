# 测试

[English](README.md) | 简体中文

## 自动检查

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

单元测试覆盖配置校验、凭据隐藏、无密码 HTTP 访问／Origin／CSRF 及宿主音量隔离、模块注册、第三音源仲裁、旧事件、释放失败、热插拔状态、WebSocket帧、日志/缓存上限及更新回滚/预检。

## 硬件集成

MP3 传输回归还使用按小块生成、长度已知的 20,850,000 字节音频流，超过 MPD 的 16MiB 完整文件缓存上限。前后定位都必须到达目标位置并继续前进；从 1000 秒返回 2 秒时必须产生新的非零 HTTP Range 请求。解码器向前定位可以在已有 HTTP 连接上读取并丢弃中间帧。报告分别记录定位请求，验收中止时也保留失败用例。

定位验收在有限超时内等待播放位置越过目标继续前进，向后定位还必须等待新请求。MPD 可能先报告目标时间，再完成异步解码和 HTTP 操作，因此仅显示目标时间不能算通过。

原生 MPD 镜像使用 `tests/mpd_mp3_ci.py <image>` 测试生成的 MPEG-1 Layer III 静音帧。先用本地解码确认夹具有效，再测试 HTTP CBR／VBR、ID3、无扩展名 audio/mpeg 和顺序输入；可定位输入验证前后定位及暂停／恢复。构建阶段还编译 `images/mpd/seek-test.cxx`，对解码器实际使用的偏移计算函数测试负目标、溢出及未知结束位置。无需用户媒体文件或额外编解码器。实机 DLNA smoke 覆盖 44.1／48kHz 带 ID3 的 MP3、44.1／48／88.2／96kHz PCM／FLAC 和已验证 DoP。在 USB 检查前后及采样率超时后核对当前 URI，将其他控制器替换夹具的情况报告为干扰，避免误判为采样率转换。

`tests/output_volume_device_smoke.py --report <私有报告路径>` 验证无密码状态访问、全新宿主单位增益初始化、0%／60% 调整、拒绝 101%、agent／WirePlumber 重启后保留音量、音源设置独立及恢复原有宿主增益。测试会短暂调整软件音量并重启这些用户服务，请保持硬件低音量。单元测试另行覆盖不可用／过期路由及调整隔离。

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

## 可回滚的应用级干净安装测试

在专用且已配置的宿主运行下列命令，会临时替换应用配置、数据和生成的服务单元，然后在 `finally` 中恢复私有状态。测试会中断播放，结束后保持暂停。硬件音量保持低，避免其他控制器操作，确认恢复前保留私有备份。它不重刷操作系统、不修改 subordinate ID 分配，也不重置宿主 PipeWire 音量。仅支持 PCM 的硬件可省略 `--dsd`。此测试不执行长时间测试。

```sh
python3 tests/clean_install_smoke.py --replace-app-state --dsd --report .local-build/clean-install.json
```

验收覆盖空配置、未配置的可选 Spotify、无密码网页状态、已选硬件缺失、重复安装保留配置、首次 API 选择 DAC、新音频服务加载、网页进程不变及实际 DLNA 格式/控制。报告除了 passed 还必须有 `private_state_restored: true`；状态恢复成功不代表之前失败的测试通过。首次广播使用有界重试，并跳过不可达或过期的设备地址。

## 解码音源采样率跟随

```sh
python3 tests/source_rate_smoke.py --report .local-build/source-rate.json
```

这个专用宿主测试会暂时停止 agent/Soloist，通过适配器提供合成 Pulse PCM，按 44.1→48→96→44.1kHz 切换，核对客户端格式、驱动图、USB、增益/静音不变、全局 force-rate 为零、修复记录不变及采样率请求清理。结束后恢复暂停服务，不运行长时间测试。它验证传输，不验证 Spotify 解码器或目录原文件格式。真实 Soloist 还须核对 PCM/USB 相等、双向 DLNA 交接、重启和听音。

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
