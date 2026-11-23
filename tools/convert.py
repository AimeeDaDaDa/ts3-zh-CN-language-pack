# -*- coding: utf-8 -*-
"""SmallFog 繁体中文包 → 简体中文包
流程: 解析旧版 QM → OpenCC tw2sp 繁转简 + 术语表 → 重建 QM 二进制 → 替换
"""
import os, struct, shutil, re
from opencc import OpenCC
from parse_qm import parse_file, parse_messages

TD = os.path.join(os.environ["APPDATA"], "TS3Client", "translations")
MAGIC = bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd")
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_tw")

FILES = ["lagos_zh.qm", "permissions_zh.qm", "ts_core_errors_zh.qm",
         "qt_zh.qm", "update_zh.qm", "error_report_zh.qm"]

cc = OpenCC("tw2sp")

# opencc 转完后再修正的术语（简体输出上的二次替换）
TERM_MAP = [
    ("设定", "设置"), ("讯息", "消息"), ("连线", "连接"),
    ("剪贴簿", "剪贴板"), ("网上", "网上"), ("音效", "音效"),
    ("软体", "软件"), ("硬体", "硬件"), ("应用程式", "应用程序"),
    ("档案", "文件"), ("资料夹", "文件夹"), ("伺服器", "服务器"),
    ("网路", "网络"), ("频宽", "带宽"), ("线下", "离线"),
    ("支援", "支持"), ("资讯", "信息"), ("使用者", "用户"),
    ("预设", "默认"), ("视窗", "窗口"), ("滑鼠", "鼠标"),
]

def t2s(text):
    out = cc.convert(text)
    for a, b in TERM_MAP:
        out = out.replace(a, b)
    return out

def parse_records(b):
    """把消息块解析成 [(tag, raw_bytes)] 有序记录, End 也作为记录保留"""
    recs, i, cur = [], 0, []
    while i < len(b):
        tag = b[i]; i += 1
        if tag == 0x01:
            recs.append(cur); cur = []
        elif tag in (0x02, 0x04):
            (n,) = struct.unpack(">H", b[i:i+2]); i += 2
            cur.append((tag, b[i:i+n*2])); i += n*2
        elif tag in (0x03,):
            (n,) = struct.unpack(">I", b[i:i+4]); i += 4
            if n == 0xFFFFFFFF:  # 未完成翻译标记, 无数据
                cur.append((tag, None))
            else:
                cur.append((tag, b[i:i+n])); i += n
        elif tag == 0x05:
            cur.append((tag, b[i:i+1])); i += 1
        elif tag in (0x06, 0x07, 0x08):
            (n,) = struct.unpack(">I", b[i:i+4]); i += 4
            cur.append((tag, b[i:i+n])); i += n
        elif tag == 0x09:
            cur.append((tag, b[i:i+4])); i += 4
        elif tag in (0x0A, 0x0B, 0x0C):
            (n,) = struct.unpack(">Q", b[i:i+8]); i += 8
            cur.append((tag, b[i:i+n*2])); i += n*2
        elif tag == 0x0D:
            cur.append((tag, b[i:i+8])); i += 8
        else:
            raise ValueError(f"tag 0x{tag:02x} @ {i-1}")
    if cur:
        recs.append(cur)
    return recs

def build_msg_block(recs):
    out = bytearray()
    for rec in recs:
        for tag, data in rec:
            out.append(tag)
            if tag in (0x02, 0x04):
                out += struct.pack(">H", len(data)//2) + data
            elif tag in (0x03, 0x06, 0x07, 0x08):
                if tag == 0x03 and data is None:  # 未完成翻译标记
                    out += struct.pack(">I", 0xFFFFFFFF)
                else:
                    out += struct.pack(">I", len(data)) + data
            elif tag == 0x05:
                out += data
            elif tag == 0x09:
                out += data
            elif tag in (0x0A, 0x0B, 0x0C):
                out += struct.pack(">Q", len(data)//2) + data
            elif tag == 0x0D:
                out += data
        out.append(0x01)
    return bytes(out)

CREDIT_KEY = "中文化版本"
CREDIT_NEW = ('<hr>\n<b>简体中文版：</b>3.0.16 <u>v1.0-CN</u> (2026/11/23)\n'
              '<br /><br /><b>基于 SmallFog 繁体中文包转换</b><br />\n')

def record_starts(blk):
    """扫描消息块, 返回每条记录的起始偏移"""
    starts, j = [], 0
    while j < len(blk):
        starts.append(j)
        while True:
            t = blk[j]; j += 1
            if t == 0x01:
                break
            elif t == 0x03:
                (n,) = struct.unpack(">I", blk[j:j+4]); j += 4
                if n != 0xFFFFFFFF:
                    j += n
            elif t in (0x02, 0x04):
                (n,) = struct.unpack(">H", blk[j:j+2]); j += 2 + n * 2
            elif t == 0x05:
                j += 1
            elif t in (0x06, 0x07, 0x08):
                (n,) = struct.unpack(">I", blk[j:j+4]); j += 4 + n
            elif t == 0x09:
                j += 4
            else:
                raise ValueError(f"tag 0x{t:02x} @ {j-1}")
    return starts

def rebuild_hashes(old_hashes, old_starts, new_starts):
    """0x42 Hashes 块 = 3253×(u32 elfHash, u32 消息偏移) 按哈希排序, 无 count 头。
    用 原偏移→记录序号→新偏移 的映射重建整张表。"""
    assert len(old_hashes) % 8 == 0
    n = len(old_hashes) // 8
    old2new = dict(zip(old_starts, new_starts))
    assert len(old2new) == len(old_starts), "记录起点重复?"
    out = bytearray()
    for k in range(n):
        h, off = struct.unpack(">II", old_hashes[k*8:(k+1)*8])
        new_off = old2new[off]
        out += struct.pack(">II", h, new_off)
    return bytes(out)

def convert_file(fname):
    path = os.path.join(TD, fname)
    d, blocks = parse_file(path)
    old_msg_blk = blocks[0x69]
    old_starts = record_starts(old_msg_blk)
    recs = parse_records(old_msg_blk)
    assert len(recs) == len(old_starts)
    changed = 0
    for rec in recs:
        for idx, (tag, data) in enumerate(rec):
            if tag in (0x03, 0x0B) and data is not None:  # translation
                text = data.decode("utf-16-be", "replace")
                if CREDIT_KEY in text:
                    new = CREDIT_NEW
                else:
                    new = t2s(text)
                if new != text:
                    rec[idx] = (tag, new.encode("utf-16-be"))
                    changed += 1
    new_msgs = build_msg_block(recs)
    new_starts = record_starts(new_msgs)
    new_hashes = rebuild_hashes(blocks[0x42], old_starts, new_starts)
    new_file = (MAGIC
                + bytes([0x42]) + struct.pack(">I", len(new_hashes)) + new_hashes
                + bytes([0x69]) + struct.pack(">I", len(new_msgs)) + new_msgs)
    return d, new_file, changed, len(recs)

if __name__ == "__main__":
    os.makedirs(BACKUP, exist_ok=True)
    total_changed = 0
    for f in FILES:
        orig, new, changed, nmsgs = convert_file(f)
        dst = os.path.join(BACKUP, f)
        if not os.path.exists(dst):  # 只备份第一次（原始繁中包）
            shutil.copy2(os.path.join(TD, f), dst)
        with open(os.path.join(TD, f), "wb") as fh:
            fh.write(new)
        total_changed += changed
        print(f"{f}: {nmsgs} 条, 转换 {changed} 条, 原始 {len(orig)}B → 新 {len(new)}B (备份于 backup_tw/)")
    # 自检: 转换后的文件能被自己的解析器完整解析
    print("---自检---")
    for f in FILES:
        d, blocks = parse_file(os.path.join(TD, f))
        msgs = parse_messages(blocks[0x69])
        print(f"{f}: 重新解析 OK, {len(msgs)} 条")
    print(f"总计转换 {total_changed} 条翻译")
