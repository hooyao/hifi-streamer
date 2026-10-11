# 在 Android 魔百盒上安装 Armbian

[English](armbian-install.md) | 简体中文

本参考说明如何将 Amlogic 魔百盒准备为 HiFi Streamer 宿主。魔百盒通常出厂运行 Android：先从 U 盘启动 Armbian，验证硬件，再按需安装到内置 eMMC。刷系统与应用安装是两个独立步骤。

## 确认硬件并准备恢复

根据主板标识及对应型号资料确认 SoC、主板版本、内存与内置存储。同一商品名可能对应不同硬件：上游适配表中 **M401A 同时出现在 S905L3 和 S905L3A 下**，不能只看外壳标签。

使用社区 [ophub/amlogic-s9xxx-armbian](https://github.com/ophub/amlogic-s9xxx-armbian) 镜像及其[设备数据库](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/build-armbian/armbian-files/common-files/etc/model_database.conf)。电视盒适配由社区维护；其他官方 Armbian 开发板镜像不能直接替代 Amlogic 盒子镜像。

准备以下物品：

- 至少 8GB 的 U 盘、装有 Rufus 等镜像写入工具的电脑，以及可靠电源。
- 有线网络及路由器 DHCP 租约查询权限；网络失败时可用 HDMI 和键盘辅助。
- 匹配的镜像、设备树配置，以及该主板对应的原厂 Android 恢复固件和操作说明。
- 需要保留的 Android 数据备份。写镜像会清空 U 盘；安装到 eMMC 会替换 Android 及其数据。恢复资料保存在另一台电脑或磁盘上。

## 选择镜像并制作 U 盘

1. 从[上游 Releases](https://github.com/ophub/amlogic-s9xxx-armbian/releases) 下载匹配的 **ARM64 server** 镜像。本项目当前验证的宿主基础是 Debian Bookworm，要求 Python 3.11 或更高版本。核对 SoC 家族和设备支持的内核分支；更新的内核不代表音频已通过验证。
2. 核对发布方提供的校验和，必要时将下载文件解压为 `.img`。
3. 在写入工具中选择目标 U 盘，将镜像按磁盘镜像写入；询问模式时使用 DD/raw 模式。把 `.img` 文件复制到普通格式化的 U 盘上不能制作启动盘。
4. 重新打开 U 盘的 boot 分区。Windows 提示格式化 Linux 分区时取消。根据设备数据库核对镜像启动配置；这类 Amlogic 镜像通常使用 `uEnv.txt`。

对于**已确认的 S905L3A 硬件**，以下设备树不能混用：

| 主板 | `uEnv.txt` 中的 `FDT` 示例 |
| --- | --- |
| M401A / S905L3A | `/dtb/amlogic/meson-g12a-s905l3a-m401a.dtb` |
| CM311-1a-YST / S905L3A | `/dtb/amlogic/meson-g12a-s905l3a-cm311.dtb` |

确认所选 DTB 文件在镜像内存在。上述示例不适用于 S905L3 变体。除非镜像说明要求修改，否则保留原 `APPEND` 的 root UUID 和其他启动参数。引导文件与 `u-boot.ext` 的要求因镜像而异，按该主板上游说明操作，不复制其他盒子的 bootloader。安全弹出 U 盘。

## 从 Android 启动 U 盘 Armbian

插入 U 盘并连接网线，使用该主板原 Android bootloader 支持的启动方式。

### Android 支持 ADB 时

固件允许时开启开发者选项和 ADB 调试。在电脑上安装 Google 的 [SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)，在工具目录执行命令或将目录加入 PATH。

对于支持传统网络 ADB 的固件，使用盒子的实际地址：

```sh
adb connect <box-address>:5555
adb devices
adb shell reboot update
```

Android 出现提示时授权电脑，重启前确认连接的是目标设备。连接了多个设备时用 `adb -s <serial>` 指定。并非所有固件都开放 5555 端口，可能需要 USB ADB 或配对式无线调试。`reboot update` 依赖原 bootloader 的更新/多重启动支持，不是通用 U 盘启动命令。

### 主板具有实体 recovery/reset 按钮时

部分盒子有复位按钮，有时位于 AV 接口深处。**仅在该主板资料明确标出按钮时**，断电、插入 U 盘，用绝缘工具按住按钮后通电，再按型号说明释放。部分魔百盒没有这个开关；不要探入未识别的孔或短接主板焊盘来模仿此步骤。

如果仍回到 Android，检查镜像、DTB、启动方式及支持的 USB 接口。无法激活 USB 多重启动的 bootloader 可能需要该主板专用的固件准备步骤，应按其恢复说明操作，不要为了尝试 USB 启动而覆盖内置 bootloader 扇区。

## 安装到 eMMC 前验证 U 盘系统

等待首次启动完成，通过路由器查询 DHCP 地址，使用 HDMI 或 SSH 登录。按所下载镜像的首次登录说明操作，并修改默认凭据。执行：

```sh
cat /etc/os-release
uname -a
cat /proc/device-tree/model
findmnt -no SOURCE,FSTYPE /
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN
sudo blkid
```

将 `findmnt` 显示的根分区来源与 `lsblk`/UUID 对照，确认它属于外接 U 盘。`/dev/sda` 很常见，但不能假定固定设备名。能 SSH 登录或看见 Armbian 启动画面不代表正在运行新 U 盘系统；以前安装过 Linux 的盒子可能仍从旧 eMMC 启动。

写 eMMC 前确认有线网络、内存/存储识别、系统稳定性和 USB DAC 发现正常：

```sh
free -h
ip -br address
cat /proc/asound/cards
dmesg --level=err,warn | tail -n 80
```

可以继续用 U 盘系统进行验证。基础系统正常后再安装 HiFi Streamer；应用不要求安装到 eMMC。应用步骤见[运行与维护](../OPERATIONS.zh-CN.md)，已验证的音频时钟规避方案见 [M401A 硬件配置](m401a.zh-CN.md)。

## 可选：安装到内置 eMMC

确认从 U 盘根分区运行、主板配置正确、有备份和恢复途径后再继续。拔掉无关存储并保持供电稳定。以下命令属于 **ophub 镜像**，不是所有 Armbian 发行方式都有：

```sh
sudo armbian-install
```

按描述选择匹配的主板条目，不照抄其他版本的菜单编号。确认目标为内置 eMMC，而非当前运行的 U 盘。提供选项时选择 `ext4` 根文件系统。没有型号专用依据时，不启用 mainline U-Boot 或修改分区工具选项。目标、主板或安装器输出与预期不符时，在确认写入前退出。

等待安装成功，按安装器说明关机。断电状态下移除 U 盘，再开机。重复根分区来源检查，确认现在从 eMMC 运行，并再次验证网口和 DAC 发现，然后继续 [HiFi Streamer 配置](../OPERATIONS.zh-CN.md)。保留启动 U 盘用于恢复。

## 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| 回到 Android | 检查 U 盘镜像写入、SoC/DTB、支持的 USB 接口，以及 Android 更新/多重启动激活步骤。 |
| 黑屏或没有 DHCP 地址 | 支持时查看 HDMI/串口输出；写 eMMC 前先核对供电、网线连接、主板 DTB 和内核支持。 |
| 启动旧 eMMC Armbian | 对照根 UUID 和启动配置。上游对部分主板提供备份并重命名旧 eMMC `/boot/boot.scr` 的方法，但这会改变备用启动路径。只有确认 U 盘镜像可用且能恢复该文件时才采用；这不是 Android 首次安装步骤。 |
| eMMC 安装失败或 I/O 错误 | 保留错误，检查电源、DTB 和存储支持，按主板恢复资料处理。反复写其他型号 bootloader 不能作为修复策略。 |
| 系统安装成功但 DAC 爆音 | 使用音频路径隔离测试及[排障指南](../debugging/troubleshooting.zh-CN.md)；能启动不代表实时音频已通过验证。 |

## 上游参考

- [支持设备及镜像发布](https://github.com/ophub/amlogic-s9xxx-armbian)
- [安装与 USB 启动文档](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.md)
- [上游中文文档](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.cn.md)

按实际下载镜像核对这些步骤，上游内核、设备条目和引导方式可能变化。本页是安装参考，不代表 HiFi Streamer 已测试所有魔百盒主板。
