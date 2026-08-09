# Webex

Not automated via `setup.toml`/`inv` — Cisco doesn't publish an apt repo, only a versioned
`.deb` download, so there's no stable URL to pin a `deb-url` package entry against. Install
manually:

1. Download the `.deb` from the [Webex download page](https://www.webex.com/downloads.html)
   (Linux section). Supported on Ubuntu 22.04 and 24.04 — 20.04 support was dropped after Webex
   45.6.
2. Install:
   ```shell
   sudo dpkg -i ~/Downloads/Webex.deb
   sudo apt install -f    # fix any missing dependencies
   ```
3. If the app launches but crashes, install the missing OpenGL library:
   ```shell
   sudo apt install -y libgl1-mesa-glx
   ```
4. If AppArmor blocks the app (common on 24.04), create an unconfined profile:
   ```shell
   sudo tee /etc/apparmor.d/local/opt.webex.bin.webex > /dev/null <<'EOF'
   /opt/webex/bin/webex flags=(unconfined) {
   }
   EOF
   sudo apparmor_parser -r /etc/apparmor.d/local/opt.webex.bin.webex
   ```
5. Verify: launch Webex, sign in, test audio/video.
