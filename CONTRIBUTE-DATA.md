# Contribute GB206 comparison data

We are looking for desktop RTX 5060 Ti (`10de:2d04`) measurements to compare with the RTX 5060 Laptop baseline. If you already have a read-only tool, the raw values and per-read status codes from that tool are welcome.

## Linux collector

[Review the collector](collect_gb206_comparison.py) before running it. The current version supports a single NVIDIA GPU on native 64-bit Linux and driver `595.99.02`. The laptop path was tested without administrator privileges. The desktop path still needs a volunteer test. Keep your existing setup if it falls outside that scope.

Download the Python file and run it from its directory:

```sh
python3 collect_gb206_comparison.py
```

Three effective TPC state words should provide the baseline. If the three candidate control words report status `0x04`, that is a valid partial result. On a matching setup, volunteers who are comfortable reviewing and running a root-level diagnostic can optionally collect a second sample:

```sh
sudo python3 collect_gb206_comparison.py
```

The collector issues six fixed 32-bit reads through the loaded driver. It prints the GPU model, PCI device ID, driver, kernel, individual statuses and available values. The JSON omits serial numbers, UUIDs and hostnames.

Paste the JSON into a [repository issue](https://github.com/jiangzechunwnl-source/gb206-tpc-research/issues/new) or reply to the [community discussion](https://github.com/physicsdolphin/nv-uefi-unlocker/discussions/216). Add the CUDA SM count if you already have it. Results with denied reads are welcome.

The collector is GPL-2.0-only. The RM allocation sequence was adapted from [gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada).

## 中文

征集桌面 RTX 5060 Ti（`10de:2d04`）的只读数据。脚本当前支持原生 64 位 Linux、单张 NVIDIA 显卡、`595.99.02` 驱动。可先用普通权限运行，直接回贴 JSON。权限拒绝也是有效记录。如果环境不匹配，已有工具读出的原始值同样欢迎。
