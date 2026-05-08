# Unraid SR-IOV Plan

Date: 2026-04-28

## Goal

Enable Intel iGPU SR-IOV on the Proxmox host and pass one VF to Unraid VM `100` so Unraid containers can use `/dev/dri` without full iGPU passthrough.

## Environment

- Proxmox host: `root@192.168.50.13`
- Unraid guest: `root@100.89.182.96`
- Target VM on Proxmox: `100` (`unraid`)

## What We Confirmed

- Proxmox iGPU PF is `00:02.0`
- GPU: Intel UHD 770 (`8086:a780`)
- Proxmox host kernel: `6.17.13-4-pve`
- Host uses `systemd-boot`, not GRUB
- Host kernel cmdline before SR-IOV change:

```text
root=ZFS=rpool/ROOT/pve-1 boot=zfs intel_iommu=on iommu=pt vfio-pci.ids=1b21:1166
```

- Hardware reports SR-IOV capability:

```text
/sys/devices/pci0000:00/0000:00:02.0/sriov_totalvfs = 7
```

- Current host `i915` driver cannot create VFs yet:

```text
i915 0000:00:02.0: driver does not support SR-IOV configuration via sysfs
```

This is why writing `sriov_numvfs` failed. The host needs the patched SR-IOV-capable Intel driver first.

## Guest-Side Findings

- Unraid kernel: `6.12.54-Unraid`
- Old plugin present: `intel-gvt-g`
- Saved legacy GVT-g VM assignment exists:

```text
/boot/config/plugins/intel-gvt-g/vms.conf
VM={Ubuntu} {i915-GVTg_V5_4} {00b2cf7e-7f42-4755-b542-c4849db5158e}
```

This old GVT-g path is for older Intel mediated-device flows and should be replaced by the newer SR-IOV path for 12th/13th/14th gen Intel graphics.

## Upstream References Used

- `strongtz/i915-sriov-dkms`
- PVE host install guide: install `build-essential`, `dkms`, `proxmox-default-headers`, then install the `i915-sriov-dkms` package
- Required host kernel parameters for `i915`:

```text
intel_iommu=on i915.enable_guc=3 i915.max_vfs=7 module_blacklist=xe
```

- Persist VF creation:

```text
devices/pci0000:00/0000:00:02.0/sriov_numvfs = 7
```

- Linux guests also need the same SR-IOV-capable driver stack

## Backups Already Taken

On the Proxmox host:

```text
/root/i915-sriov-backup-20260428-083743/
```

Contains:

- `/etc/kernel/cmdline`
- `/etc/default/grub`
- `/etc/modprobe.d/*` when present

## Where We Paused

We started installing the Proxmox host prerequisites:

```text
apt-get update && apt-get install -y build-essential dkms sysfsutils proxmox-default-headers wget
```

At interruption time, `apt/dpkg` was still running and unpacking/configuring `proxmox-headers-6.17.13-4-pve`. It looked slow, but it was not a design blocker. Before resuming, verify whether `apt` finished cleanly.

## Resume Checklist

1. On Proxmox, verify no `apt`/`dpkg` process is still active and repair package state if needed.
2. Install the patched `i915-sriov-dkms` package on Proxmox.
3. Update `/etc/kernel/cmdline` to:

```text
root=ZFS=rpool/ROOT/pve-1 boot=zfs intel_iommu=on iommu=pt vfio-pci.ids=1b21:1166 i915.enable_guc=3 i915.max_vfs=7 module_blacklist=xe
```

4. Run `proxmox-boot-tool refresh`.
5. Install `sysfsutils` persistence:

```text
devices/pci0000:00/0000:00:02.0/sriov_numvfs = 7
```

6. Reboot the Proxmox host.
7. After reboot, verify VF devices exist, expected as additional functions under the iGPU.
8. In Unraid, remove or disable the old `intel-gvt-g` path.
9. Install the Unraid `i915-sriov` plugin/driver stack.
10. Attach one VF to Proxmox VM `100`.
11. Boot Unraid and verify the VF binds to `i915` inside the guest.
12. Validate `/dev/dri`, `vainfo`, and container hardware transcoding.

## Expected Risks

- Proxmox reboot required
- Out-of-tree Intel GPU driver on the host
- Guest-side plugin migration from old GVT-g to SR-IOV
- VF numbering and guest PCI placement may need one adjustment after first boot
