# -*- coding: utf-8 -*-
"""解析旧版 QM（SmallFog 包，Qt3/4 时代格式）
消息块内 tag（经验验证）:
  01 End
  02 SourceText16: u16 len + utf16be
  03 Translation:  u32 len + utf16be（多行时 lrelease 旧版用多行? 先按单块处理）
  04 Context16:    u16 len + utf16be
  05 Obsolete1:    u8
  06 SourceText8:  u32 len + utf8   (经验: 06 00000005 "About")
  07 Comment8:     u32 len + utf8
  08 Context8:     u32 len + utf8
  09 Hash:         4 bytes
"""
import struct, os, sys

def parse_messages(b):
    msgs, i, cur = [], 0, {}
    while i < len(b):
        tag = b[i]; i += 1
        if tag == 0x01:
            msgs.append(cur); cur = {}
        elif tag == 0x02:
            (n,) = struct.unpack(">H", b[i:i+2]); i += 2
            cur["src"] = b[i:i+n*2].decode("utf-16-be", "replace"); i += n*2
        elif tag == 0x03:
            (n,) = struct.unpack(">I", b[i:i+4]); i += 4
            if n == 0xFFFFFFFF:  # 未完成翻译标记
                cur["tr"] = None
            else:
                cur["tr"] = b[i:i+n].decode("utf-16-be", "replace"); i += n
        elif tag == 0x04:
            (n,) = struct.unpack(">H", b[i:i+2]); i += 2
            cur["ctx"] = b[i:i+n*2].decode("utf-16-be", "replace"); i += n*2
        elif tag == 0x05:
            cur["obs"] = b[i]; i += 1
        elif tag in (0x06, 0x07, 0x08):
            (n,) = struct.unpack(">I", b[i:i+4]); i += 4
            key = {0x06: "src", 0x07: "cmt", 0x08: "ctx"}[tag]
            cur[key] = b[i:i+n].decode("utf-8", "replace"); i += n
        elif tag == 0x09:
            cur["hash"] = b[i:i+4]; i += 4
        elif tag in (0x0A, 0x0B, 0x0C, 0x0D):
            (n,) = struct.unpack(">Q", b[i:i+8]); i += 8
            key = {0x0A: "src", 0x0B: "tr", 0x0C: "ctx"}[tag]
            cur[key] = b[i:i+n*(2 if tag != 0x0D else 1)].decode("utf-16-be", "replace") if tag != 0x0D else b[i:i+n].hex()
        else:
            raise ValueError(f"unknown tag 0x{tag:02x} @ {i-1}, cur={cur}")
    if cur:
        msgs.append(cur)
    return msgs

def parse_file(path):
    d = open(path, "rb").read()
    assert d[:16] == bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd")
    i, blocks = 16, {}
    while i + 5 <= len(d):
        tag = d[i]; (size,) = struct.unpack(">I", d[i+1:i+5])
        blocks[tag] = d[i+5:i+5+size]
        i += 5 + size
    return d, blocks

if __name__ == "__main__":
    TD = os.path.join(os.environ["APPDATA"], "TS3Client", "translations")
    for f in ["lagos_zh.qm", "permissions_zh.qm", "ts_core_errors_zh.qm", "qt_zh.qm",
              "update_zh.qm", "error_report_zh.qm"]:
        p = os.path.join(TD, f)
        try:
            d, blocks = parse_file(p)
            msgs = parse_messages(blocks[0x69])
            done = [m for m in msgs if m.get("tr")]
            print(f"{f}: blocks={sorted(blocks)} 消息{len(msgs)} 已译{len(done)}")
            if f == "lagos_zh.qm":
                for m in msgs[:6]:
                    print("   ", {k: (v if not isinstance(v, bytes) else v.hex()) for k, v in m.items()})
        except Exception as e:
            print(f"{f}: FAIL {e}")
