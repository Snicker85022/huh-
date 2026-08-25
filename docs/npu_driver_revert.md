# NPU (amdxdna) driver — staging load & DKMS revert procedures

Status: 2026-08-25. Applies to the XDNA1 NPU on gflip (PCI 1022:1502, /dev/accel/accel0).

## Verified facts (this machine, this boot)

- Mainline module present: `/lib/modules/7.0.0-30-generic/kernel/drivers/accel/amdxdna/amdxdna.ko.zst`
- Mainline `srcversion`: `E4FC5AFFF53D21BC6AFDAE3` (also the value of `/sys/module/amdxdna/srcversion` right now — mainline is currently loaded)
- `dkms` is NOT installed; there is NO `/lib/modules/$(uname -r)/updates/dkms/` shadow module
- Mainline reload was already exercised successfully this session (firmware 1.5.5.391 install did
  `modprobe -r amdxdna` + `modprobe amdxdna`; dmesg: `Initialized amdxdna_accel_driver 0.7.0`), and
  `/dev/accel/accel0` came back.

## Decision (NPU Phase 1 testing)

- The XRT **plugin deb** (`xrt_plugin.*-amdxdna.deb`) is the ONLY artifact that installs a persistent
  DKMS driver. It is **NOT required** for Phase 1-4. We do NOT install it. Phase 1 tests mainline first,
  and only if telemetry/array ioctls fail do we load the **staging** driver session-only (see below).
- The XRT **base debs** (`xrt_*-base.deb`, `xrt_*-base-dev.deb`) are pure userspace (libraries + xrt-smi
  tool). They install NO kernel module and do NOT trigger DKMS.
- The SHIM libraries (`libvxdna.so`, `libxrt_driver_xdna.so`) and `shim_test` come from building the
  plugin tree `(cd build && ./build.sh -release)` WITHOUT installing it; Fix #1 copies the .so files
  manually into /opt/xilinx/xrt/lib. That is the documented non-DKMS path.

## Procedure A — staging driver, session-only (the only driver swap used in this testing)

```bash
# LOAD (staging, session-only; built from amd/xdna-driver, vermagic == running kernel):
sudo bash /home/taza/npu-tests/open-xdna/scripts/swap_driver.sh \
  /home/taza/npu-tests/xdna-driver/build/Release/bins/driver/amdxdna.ko
# verify: cat /sys/module/amdxdna/srcversion   (will differ from mainline E4FC5AFF...)

# REVERT (restore mainline) — either one:
sudo modprobe -r amdxdna && sudo modprobe amdxdna   # mainline reloads from its kernel dir
# OR simply reboot (mainline auto-loads; nothing persists)
# verify: cat /sys/module/amdxdna/srcversion        # expect E4FC5AFFF53D21BC6AFDAE3
#         ls -l /dev/accel/accel0                  # expect present
```

## Procedure B — DKMS persistence (NOT used now; documented in case it is ever chosen)

If, in the future, someone installs `xrt_plugin.*-amdxdna.deb` (it registers a DKMS module), the revert is:

```bash
# 1. Remove the plugin package (this triggers dkms remove for its module):
sudo apt remove xrt-plugin-amdxdna          # exact pkg name as shown by `dpkg -l | grep xrt`
#    or, to remove ONLY the DKMS module while keeping the package:
sudo dkms remove amdxdna/<version> --all    # <version> = what `dkms status` lists after install

# 2. Confirm no DKMS module shadows mainline:
dkms status                                  # amdxdna must NOT be listed
ls /lib/modules/$(uname -r)/updates/dkms/   # must not exist / be empty
sudo depmod -a

# 3. Reload mainline (it is untouched; it lives in the kernel's own module tree):
sudo modprobe -r amdxdna 2>/dev/null; sudo modprobe amdxdna

# 4. Verify mainline is back:
cat /sys/module/amdxdna/srcversion           # expect E4FC5AFFF53D21BC6AFDAE3
ls -l /dev/accel/accel0                     # expect crw-rw---- root render 261,0
```

Because dkms is not installed and no updates/dkms shadow dir exists, removing the plugin restores the
exact state that exists right now. Mainline reloadability is already proven (see "Verified facts").
