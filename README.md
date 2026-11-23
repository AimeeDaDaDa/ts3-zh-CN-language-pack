# TeamSpeak 3 简体中文语言包

TeamSpeak 3 Client（3.6.x）简体中文界面语言包。基于 SmallFog 的繁体中文语言包（3.0.16 v1.0）繁转简制作。

> 繁体原作：SmallFog — https://sites.google.com/site/ts3taiwan
> 本包为繁转简衍生版本，版权归原作者所有，仅供学习交流，请勿商用。

## 安装

Windows / macOS：直接**双击** `Chinese_Simplified.ts3_translation`，客户端会自动安装。
若双击无效，用 TeamSpeak 安装目录下的 `package_inst.exe` 打开该文件。

安装后：工具 → 选项 → 语言（或应用设置里的语言下拉框）选择 `zh` / 中文即可。
（语言代码为 `zh`，与常见 TS3 中文设置一致。）

## 覆盖范围

| 文件 | 内容 | 条数 |
|------|------|------|
| lagos_zh.qm | 客户端主界面 | 3253 |
| permissions_zh.qm | 权限系统 | 496 |
| qt_zh.qm | Qt 组件 | 1531 |
| ts_core_errors_zh.qm | 错误码 | 185 |
| update_zh.qm | 更新器 | 29 |
| error_report_zh.qm | 错误报告 | 5 |

共 5487 条文本，其中 5475 条已转为简体（12 条原繁体包即未翻译）。
全部消息已通过 Qt QTranslator 逐条校验（5487/5487 命中），兼容 Qt6 内核的 TS3 客户端 3.6.2。

## tools/ 目录

`parse_qm.py` / `convert.py` 为本包的制作工具（QM 解析 + OpenCC 繁转简重建），
转换时重建了 QM 内部 Hashes 偏移表，供后续维护/更新使用。

## 更新说明

- v1.0-CN (2026-11-23)：首版。基于 SmallFog 3.0.16 v1.0 繁体包全量繁转简。
