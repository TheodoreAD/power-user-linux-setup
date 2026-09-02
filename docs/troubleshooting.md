# Troubleshooting

Fixes for this machine's own hardware quirks: sensors, GPU, and the workarounds that were not
obvious.

## Hardware sensors — fan and voltage monitoring on Gigabyte Z390

**Board:** Gigabyte Z390 GAMING X · **Chip:** ITE IT8628E at I/O port 0xa40

### What works out of the box

Temperature data is available via two hwmon drivers loaded automatically:

- `gigabyte_wmi` (hwmon2) — 6 system temps from BIOS WMI (VRM, PCH, etc.)
- `coretemp` (hwmon3) — 7 readings: CPU Package + 6 individual cores

`sensors` shows all of these. Vitals reads from `/sys/class/hwmon/` and displays them.

### What doesn't work: fans and voltages

The IT8628E SuperIO chip that reads fan headers and voltage rails is present at ISA port 0xa40, but
the BIOS registers those ports in the ACPI namespace, blocking the `it87` kernel driver from
claiming them:

```
# it87 finds the chip but can't register the port:
it87: Found IT8628E chip at 0xa40, revision 1
modprobe: ERROR: could not insert 'it87': Device or resource busy

# Other drivers also fail:
modprobe nct6775  → No such device
modprobe nct6683  → No such device
```

`sensors-detect` does not find the chip because the ACPI port conflict prevents `it87` from loading
even during detection.

### Fix (requires reboot)

Add `acpi_enforce_resources=lax` to the GRUB kernel command line. This tells the kernel to allow
hwmon drivers to claim I/O ports even if ACPI has registered them — safe on desktop boards, standard
fix for this class of SuperIO conflict.

```shell
sudo sed -i \
  's/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash acpi_enforce_resources=lax"/' \
  /etc/default/grub
sudo update-grub
# reboot
```

After reboot, load the driver and make it persistent:

```shell
sudo modprobe it87
sensors   # should now show fan RPM and voltages from it8628-isa-0a40
# If sensors still needs a label mapping, run: sudo sensors-detect
echo "it87" | sudo tee /etc/modules-load.d/it87.conf
```

### Decision (2026-06-09)

Not applied. `acpi_enforce_resources=lax` is a GRUB change and the payoff (fans + voltages in
Vitals) was judged not worth the reboot and boot-parameter risk for now. Vitals is configured to
show temperatures only. Revisit if fan monitoring becomes important (e.g. before overclocking or in
a hot environment).

---

## GRUB — GPU driver conflicts at boot (`nomodeset`)

Some machines (particularly with older NVIDIA or AMD discrete GPUs) show a blank screen or freeze
during boot because the kernel tries to take over framebuffer mode before GPU drivers are loaded.
The fix is `nomodeset`, which tells the kernel not to set video modes — the GPU driver handles it
instead.

**Only apply this if you are experiencing boot issues.** On most modern hardware with Ubuntu 24.04
it is not needed.

```shell
sudo sed -i \
  's~GRUB_CMDLINE_LINUX_DEFAULT=.*~GRUB_CMDLINE_LINUX_DEFAULT="nomodeset"~' \
  /etc/default/grub
sudo update-grub
```

Reboot to apply. The only downside is cosmetic: no splash screen, verbose boot output.

To undo, restore `GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"` and run `sudo update-grub` again.

## Fix CRLF line endings

If you receive files from Windows machines, they may have `\r\n` line endings that break shell
scripts and tools. `dos2unix` is installed by default in this setup.

```shell
# Check how many files have CRLF
find . -type f | xargs file -k -- | grep CRLF | wc -l

# Fix all files recursively
find . -type f | xargs dos2unix

# After fixing, clean up stale permission bits if needed
chmod go-w -R *
sudo find . -type f | xargs chmod a-x
```

## IBus Ctrl+Shift+U shortcut conflict

On Ubuntu with the IBus input method, `Ctrl+Shift+U` is bound to "Unicode code point input" by
default. This conflicts with some terminal workflows and applications.

To disable it:

1. Run `ibus-setup` (or open IBus Preferences from the system tray)
2. Go to the **Emoji** tab
3. Find **Unicode code point:** and click the `...` button
4. Click **Delete**, then **OK**
5. Close IBus Preferences

The shortcut is now free for other uses.

## HDMI audio (NVidia)

### Problem

No audio output when using a TV or monitor connected via HDMI to an NVidia GPU, even though video
works fine. The TV works correctly with other machines.

### Root cause

The NVidia HDMI audio device is a separate PCI function (`01:00.1`) from the GPU (`01:00.0`). It
exposes audio capability to the OS via ELD (EDID-Like Data), which the GPU driver reads from the
connected display's EDID and passes to the HDA audio driver. If the audio PCI function initializes
before the GPU driver has finished negotiating the HDMI link, it misses the ELD handoff and sees no
monitor.

You can confirm this is the issue:

```bash
grep -h 'monitor_present\|eld_valid' /proc/asound/card2/eld*
```

A broken state shows only:

```
eld_valid       0
monitor_present 0
```

A healthy state also includes `eld_valid 1` and `monitor_present 1` in the output.
`monitor_present 0` on all entries means the HDA audio driver has no idea a display is connected, so
PipeWire marks the HDMI sink as **suspended** and audio never plays.

Note: there are many ELD entries (one per pin/device combination). The active one after the fix will
be whichever pin the display is actually connected to — not necessarily `eld#0.0`. Check all of them
with the grep above.

### Investigation steps

```bash
# Confirm PipeWire is running and HDMI is the default sink
wpctl status

# Check the sink state — "suspended" here is the symptom
pw-cli info <sink-id> | grep state

# Check ELD data for all HDMI ports on the NVidia card
cat /proc/asound/card2/eld*

# Confirm the GPU/audio PCI functions
lspci -k | grep -A3 'VGA\|Audio'
# 01:00.0  VGA  — NVidia GA104, driver: nvidia
# 01:00.1  Audio — NVidia GA104 HDA, driver: snd_hda_intel
```

### Fix

Force the NVidia HDMI audio PCI function to re-initialize, which causes it to re-read the ELD from
the running GPU driver:

```bash
sudo sh -c "echo 1 > /sys/bus/pci/devices/0000:01:00.1/remove"
sudo sh -c "echo 1 > /sys/bus/pci/rescan"
```

No reboot needed. Video is unaffected (that's `01:00.0`; this only touches `01:00.1`).

Verify it worked:

```bash
grep -h 'monitor_present\|eld_valid' /proc/asound/card2/eld*
# should include:
# eld_valid       1
# monitor_present 1
```

PipeWire will now see the HDMI sink as active. The sink will still show as "suspended" when idle —
that is normal. It will activate when audio plays.

### Making it permanent

This fix does **not** survive a reboot. The PCI remove/rescan is a one-shot operation. If the
problem recurs after rebooting, a systemd service can automate it:

```ini
# /etc/systemd/system/nvidia-hdmi-audio-fix.service
[Unit]
Description=Re-initialize NVidia HDMI audio after GPU driver loads
After=systemd-modules-load.service nvidia-persistenced.service
Wants=sound.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo 1 > /sys/bus/pci/devices/0000:01:00.1/remove"
ExecStart=/bin/sh -c "echo 1 > /sys/bus/pci/rescan"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable with:

```bash
sudo systemctl enable --now nvidia-hdmi-audio-fix.service
```

System details at time of writing: NVidia GA104 (RTX 3070 Ti), proprietary driver, `snd_hda_intel`
on PCI `01:00.1`, PipeWire 1.0.5 with WirePlumber.

## See also

- [Input devices](input_devices.md) — peripheral-specific notes
- [Networking](networking.md) — when the problem is connectivity rather than hardware
