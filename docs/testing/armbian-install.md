# Install Armbian on an Android TV box

English | [简体中文](armbian-install.zh-CN.md)

This reference explains how to prepare a Mobaihe (魔百盒) Amlogic TV box for HiFi Streamer. These boxes usually ship with Android: first boot Armbian from a USB drive, verify the hardware, then optionally install it to internal eMMC. The firmware procedure is separate from the application's installer.

## Identify the hardware and prepare recovery

Confirm the SoC, board revision, RAM and internal storage from the board markings and model-specific documentation. The same retail name can cover different hardware: upstream lists **M401A under both S905L3 and S905L3A**. A case label alone is insufficient.

Use the community [ophub/amlogic-s9xxx-armbian](https://github.com/ophub/amlogic-s9xxx-armbian) images and its [device database](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/build-armbian/armbian-files/common-files/etc/model_database.conf). TV-box support is community maintained; an arbitrary official Armbian board image is not interchangeable with an Amlogic TV-box image.

Prepare:

- A USB drive of at least 8GB, a computer with an image writer such as Rufus, and a reliable power supply.
- Wired Ethernet and access to the router's DHCP leases; HDMI and a keyboard are useful if networking fails.
- A matching image, device-tree configuration and the original Android recovery firmware/instructions for the exact board.
- Backups of anything needed from Android. Writing the USB image erases the USB drive; installing to eMMC replaces Android and its data. Keep recovery files on another computer or disk.

## Choose an image and write the USB drive

1. Download a matching **ARM64 server** image from [upstream releases](https://github.com/ophub/amlogic-s9xxx-armbian/releases). Debian Bookworm is the currently qualified host base for this project; Python 3.11 or later is required. Match the SoC family and the device's supported kernel branch. A newer kernel is not automatically qualified for audio.
2. Check any checksum supplied by the publisher and decompress the download to `.img` if needed.
3. Select the USB drive in the writer and write the image as a disk image, using DD/raw mode if prompted. Copying the `.img` file onto a formatted drive does not create a bootable installation.
4. Reopen the USB's boot partition. If Windows asks to format the Linux partition, cancel. Check the image's boot configuration, normally `uEnv.txt` for these Amlogic images, against the device database.

For **confirmed S905L3A hardware**, these device-tree examples are distinct:

| Board | `FDT` example in `uEnv.txt` |
| --- | --- |
| M401A / S905L3A | `/dtb/amlogic/meson-g12a-s905l3a-m401a.dtb` |
| CM311-1a-YST / S905L3A | `/dtb/amlogic/meson-g12a-s905l3a-cm311.dtb` |

Verify the selected DTB exists in the image. These examples do not apply to an S905L3 variant. Preserve the image's `APPEND` root UUID and other boot parameters unless its instructions require a change. Bootloader files and `u-boot.ext` requirements vary by image; follow the exact board's upstream instructions instead of copying a bootloader from another box. Safely eject the drive.

## Boot from Android into USB Armbian

Insert the USB drive and connect Ethernet. Use the startup method supported by the board's existing Android bootloader.

### Android with ADB access

Enable Android developer options and ADB debugging if the installed firmware allows it. Install Google's [SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) on the computer and run commands from that directory or add it to PATH.

For firmware that supports legacy network ADB, use the box's actual address:

```sh
adb connect <box-address>:5555
adb devices
adb shell reboot update
```

Authorize the computer on Android when prompted and verify the intended device is connected before rebooting. If multiple devices are attached, use `adb -s <serial>` for the command. Port 5555 is not enabled on all firmware; USB ADB or Android's paired wireless debugging may be required. `reboot update` depends on the original bootloader's update/multiboot support. It is not a universal USB-boot command.

### Board with a physical recovery/reset button

Some boxes expose a reset button, sometimes behind the AV connector. **Only if the exact board's instructions identify that button**, power off, insert the USB drive, hold the button with a nonconductive tool and apply power; release it as directed by those instructions. Some Mobaihe boards have no such switch. Do not probe unidentified holes or short board pads to imitate this method.

If the box returns to Android, verify the image, DTB, startup method and supported USB port. A bootloader that cannot activate USB multiboot may require a board-specific firmware preparation step; use its documented recovery procedure. Do not overwrite internal bootloader sectors merely to try to make USB boot work.

## Verify the USB system before installing to eMMC

Allow the first boot to complete, find the DHCP address and connect through HDMI or SSH. Follow the downloaded image's first-login instructions and change its default credentials. Inspect:

```sh
cat /etc/os-release
uname -a
cat /proc/device-tree/model
findmnt -no SOURCE,FSTYPE /
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN
sudo blkid
```

Trace the root source reported by `findmnt` through `lsblk`/UUIDs to the external USB drive. `/dev/sda` is common but is not a guaranteed device name. An SSH login or an Armbian boot screen alone does not prove the new USB system is running; a box previously installed with Linux may still boot its old eMMC installation.

Verify wired networking, correct RAM/storage detection, stable operation and USB DAC discovery before touching eMMC:

```sh
free -h
ip -br address
cat /proc/asound/cards
dmesg --level=err,warn | tail -n 80
```

Keep the system on USB for qualification if desired. Install HiFi Streamer after the base OS is working; the application does not require an eMMC installation. See [operations](../OPERATIONS.md) and the [M401A hardware profile](m401a.md) for the qualified audio-clock workaround.

## Optional: install to internal eMMC

Proceed only after confirming USB-root boot, the correct board profile, a backup and a recovery path. Disconnect unrelated storage and keep power stable. The following command belongs to the **ophub image**, not every Armbian distribution:

```sh
sudo armbian-install
```

Select the matching board entry by its description, not a menu number copied from another version. Confirm the destination is internal eMMC rather than the running USB drive. Use `ext4` for the root filesystem when offered. Do not enable mainline U-Boot or change partition-tool options without model-specific guidance. If the target, board or installer output differs from expectations, exit before confirming writes.

Wait for successful completion and follow the installer's shutdown instructions. Remove the USB drive while powered off, then boot again. Repeat the root-source checks to confirm the system now runs from eMMC, and verify Ethernet and DAC detection before following [HiFi Streamer setup](../OPERATIONS.md). Keep the bootable USB drive for recovery.

## Common failures

| Symptom | Checks and next step |
| --- | --- |
| Returns to Android | Check USB image writing, correct SoC/DTB, supported USB port and Android update/multiboot activation. |
| Black screen or no DHCP lease | Inspect HDMI/serial output where supported; verify power, Ethernet link, board DTB and kernel support before attempting eMMC writes. |
| Boots an old eMMC Armbian installation | Compare root UUIDs and boot configuration. Upstream documents backing up/renaming an old eMMC `/boot/boot.scr` for certain boards, but it changes the fallback boot path. Use that procedure only with a confirmed working USB image and a way to restore the file; it is not a first-install step for Android. |
| eMMC install fails or reports I/O errors | Preserve the error, check power, DTB and storage support, and use board-specific recovery guidance. Repeatedly writing another model's bootloader is not a repair strategy. |
| DAC pops despite successful OS installation | Use the audio-path isolation tests and [troubleshooting guide](../debugging/troubleshooting.md); successful boot does not qualify real-time audio. |

## Upstream references

- [Supported devices and image releases](https://github.com/ophub/amlogic-s9xxx-armbian)
- [Installation and USB startup documentation](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.md)
- [Chinese upstream documentation](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.cn.md)

Match these instructions to the image you actually download; upstream kernels, device entries and boot procedures can change. This is an installation reference, not a claim that every Mobaihe board has been tested by HiFi Streamer.
