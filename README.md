# GB206 TPC floorsweeping research

**Have a desktop RTX 5060 Ti? [Collect and share a read-only sample](CONTRIBUTE-DATA.md).**

Looking for a read-only comparison from a desktop RTX 5060 Ti (GB206). This project measures the enabled TPC/SM topology on an RTX 5060 Laptop. The source of the disabled bits and the health of those units are open questions.

## RTX 5060 Laptop measurements

Hardware: RTX 5060 Laptop GPU (PCI device ID `10de:2d59`). Linux `7.0.0-42-generic`, NVIDIA open kernel driver `595.99.02`. NVIDIA RM reported 4, 4 and 5 enabled TPCs across three logical GPCs. CUDA reported 26 SMs. The per-GPC enabled masks were `0x3a / 0x3a / 0x3e`.

| BAR0 offset | 32-bit result | Interpretation |
| --- | --- | --- |
| `0x820c1c` | `0x00000ff8` | Effective GPC state |
| `0x820c38` | `0x000000c5` | Effective TPC state, GPC 0 |
| `0x820c3c` | `0x000000c5` | Effective TPC state, GPC 1 |
| `0x820c40` | `0x000000c1` | Effective TPC state, GPC 2 |
| `0x820838`, `0x82083c`, `0x820840` | `0x00000000` each | GA100 CTRL analogs. GB206 field semantics unconfirmed. |
| `0x820768` | `0xbadf5040` | Consistent with a GPU access-error response. Raw TPC data unavailable through this path. |

The low six bits of each inverted TPC state match the RM masks. The sampled values also match when inverted and truncated to eight bits, so this sample alone cannot establish the hardware mask width.

Method: NVIDIA RM control `0x20800122` (REG_OPS), 32-bit global reads, per-operation status enabled via `bNonTransactional`. The administrator batch contained `0x820c38` and `0x820c40` as controls, three CTRL analogs and `0x820768`. All six operations returned status zero. The ordinary-user batch returned both controls and rejected the other four at host-side permission validation (per-operation `0x04`). The earlier effective-state batch supplied `0x820c1c` and `0x820c3c`. No register writes were used.

Offline GSP check: the GB206 GraphicsManager path uses relative `0xc38 + 4 × GPC` for effective state. The identified GA100 merge routine reads relative `0x838 + 4 × GPC`; the corresponding GB206 constructor slot selects a stub on the paths checked. The firmware image studied was `gsp_ga10x.bin`, SHA-256 `f2848c5da315a636a4b03945b9edebb762eda2140df750ce2cf140b9d4b19fc3`.

## What to share

If you have an RTX 5060 Ti and an existing read-only diagnostic setup, please [open an issue here](https://github.com/jiangzechunwnl-source/gb206-tpc-research/issues/new) with:

- Exact model, PCI device ID, driver version, OS and read method.
- Raw values and individual read statuses for `0x820c38 / 0x820c3c / 0x820c40` and `0x820838 / 0x82083c / 0x820840`, if available.
- CUDA SM count and per-GPC enabled masks, if available.

Partial results and access errors are useful. Please omit serial numbers, GPU UUIDs, hostnames and full system logs. Verified GB206 documentation or firmware references for the fields are also welcome. The immediate comparison is whether the three candidate words vary when the effective TPC state differs. An actual core recovery claim would require separate evidence of scheduling and successful computation on additional SMs.

Related work: [Ampere/Ada TPC diagnostics](https://github.com/physicsdolphin/nv-uefi-unlocker/issues/169).

## 中文说明

征集桌面 RTX 5060 Ti（GB206）的只读对照。笔记本 RTX 5060 已测到 13 个 TPC、26 个 SM。请在本仓库 Issue 贴上表中的三组有效状态、三个候选控制字，以及显卡型号、驱动版本和读取方法。只有部分数据或读到错误值也可以。重点是确认这些候选值是否随同芯片的启用配置变化，以及有没有可核验的 GB206 字段定义。
