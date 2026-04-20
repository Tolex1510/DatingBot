import json
import time

# фиксированный базовый overhead JSON-обёртки {"seq":X,"ts":Y,"p":"..."}
# реальный размер сообщения = target_size; если target_size < минимума — добиваем минимумом
_MIN_SIZE = 64


def build(seq: int, target_size: int) -> bytes:
    size = max(target_size, _MIN_SIZE)
    # сначала считаем обёртку с пустым payload, потом добиваем до нужной длины
    skeleton = json.dumps({"seq": seq, "ts": time.time(), "p": ""}, separators=(",", ":"))
    overhead = len(skeleton.encode("utf-8"))
    pad_len = max(size - overhead, 0)
    body = json.dumps(
        {"seq": seq, "ts": time.time(), "p": "x" * pad_len},
        separators=(",", ":"),
    ).encode("utf-8")
    return body


def parse(raw: bytes) -> tuple[int, float]:
    obj = json.loads(raw)
    return int(obj["seq"]), float(obj["ts"])
