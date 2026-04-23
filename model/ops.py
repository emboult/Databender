import random
from typing import Optional


def glitch_randomize(state, history=None, rng: Optional[random.Random] = None, **kwargs):
    sel = state.get_selection_range()
    if not sel:
        return
    start, end = sel
    if end < start:   # den prepei na ginei alla safety
        return
    # [start, end]
    before = bytes(state.current[start:end+1])
    if rng is None:
        rng = random.Random()
    after = bytes(rng.randint(0, 255) for _ in range(len(before)))
    state.set_bytes(start, after, replace_len=len(before))
    if history is not None and hasattr(history, 'push'):
        history.push((start, before, after))


def glitch_invert(state, history=None, **kwargs):
    sel = state.get_selection_range()
    if not sel:
        return
    start, end = sel
    if end < start:
        return
    before = bytes(state.current[start:end+1])
    after_b = bytes([b ^ 0xFF for b in before])
    state.set_bytes(start, after_b, replace_len=len(before))
    if history is not None and hasattr(history, 'push'):
        history.push((start, before, after_b))


def glitch_zero(state, history=None, **kwargs):
    sel = state.get_selection_range()
    if not sel:
        return
    start, end = sel
    if end < start:
        return
    before = bytes(state.current[start:end+1])
    after_b = bytes([0x00] * len(before))
    state.set_bytes(start, after_b, replace_len=len(before))
    if history is not None and hasattr(history, 'push'):
        history.push((start, before, after_b))


def whitespace_inject(state, history=None, count: int = 1, rng: Optional[random.Random] = None, **kwargs):
    if not getattr(state, 'current', None) or count <= 0:
        return 0
    if rng is None:
        rng = random.Random()
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    positions = []
    if sel:
        start, end = sel
        if end < start:
            return 0
        # insertion can be before start or after end, so range [start, end+1]
        for _ in range(count):
            positions.append(rng.randint(start, end+1))
    else:
        for _ in range(count):
            positions.append(rng.randint(0, len(state.current)))

    positions.sort(reverse=True)
    inserted = 0
    for pos in positions:
        byte = rng.choice([0x09, 0x0A, 0x20])
        try:
            state.current.insert(pos, byte)
            inserted += 1
        except Exception:
            pass
    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return inserted


def repeat_chunks(state, history=None, size: int = 1, repeats: int = 1, rng: Optional[random.Random] = None, **kwargs):
    if not getattr(state, 'current', None) or size <= 0 or repeats <= 0:
        return 0
    if rng is None:
        rng = random.Random()
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    positions = []
    if sel:
        start, end = sel
        if end < start or size > (end - start + 1):
            return 0
        max_pos = max(start, end - size + 1)
        for _ in range(repeats):
            if max_pos >= start:
                positions.append(rng.randint(start, max_pos))
    else:
        if size > len(state.current):
            return 0
        max_pos = len(state.current) - size
        for _ in range(repeats):
            positions.append(rng.randint(0, max_pos))

    positions.sort(reverse=True)
    inserted = 0
    for pos in positions:
        try:
            chunk = state.current[pos:pos + size]
            state.current[pos:pos] = chunk
            inserted += 1
        except Exception:
            pass
    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return inserted


def pattern_inject(state, history=None, pattern: bytes = b"", count: int = 1, rng: Optional[random.Random] = None, **kwargs):
    if not getattr(state, 'current', None) or not pattern or count <= 0:
        return 0
    if rng is None:
        rng = random.Random()
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    positions = []
    if sel:
        start, end = sel
        if end < start:
            return 0
        for _ in range(count):
            positions.append(rng.randint(start, end+1))
    else:
        for _ in range(count):
            positions.append(rng.randint(0, len(state.current)))
    positions.sort(reverse=True)
    inserted = 0
    for pos in positions:
        try:
            state.current[pos:pos] = pattern
            inserted += 1
        except Exception:
            pass
    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return inserted


def shuffle_blocks(state, history=None, block_size: int = 1, rng: Optional[random.Random] = None, **kwargs):
    if not getattr(state, 'current', None) or block_size <= 0:
        return 0
    if rng is None:
        rng = random.Random()
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    try:
        if sel:
            start, end = sel
            if end < start:
                return 0
            data = state.current[start:end+1]
            blocks = [bytes(data[i:i+block_size]) for i in range(0, len(data), block_size)]
            if len(blocks) > 1:
                rng.shuffle(blocks)
            new = b''.join(blocks)
            state.set_bytes(start, new, replace_len=len(data))
        else:
            header = state.current[:512]
            body = state.current[512:]
            blocks = [bytes(body[i:i+block_size]) for i in range(0, len(body), block_size)]
            if len(blocks) > 1:
                rng.shuffle(blocks)
            new_body = b''.join(blocks)
            state.set_bytes(512, new_body, replace_len=len(body))
    except Exception:
        return 0
    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return 1


def hex_pattern_replace(state, history=None, pattern: str = "", replace: bytes = b"", **kwargs):
    if not getattr(state, 'current', None) or not pattern or not replace:
        return 0

    def parse_pattern(pat_str: str):
        tokens = []
        s = pat_str.replace(" ", "")
        if len(s) % 2 != 0:
            raise ValueError("Odd length")
        i = 0
        while i < len(s):
            pair = s[i:i+2]
            if pair == '..':
                tokens.append(None)
            else:
                tokens.append(int(pair, 16))
            i += 2
        return tokens

    tokens = parse_pattern(pattern)
    plen = len(tokens)
    if plen == 0:
        return 0
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    data = bytes(state.current)

    def replace_body(src: bytes):
        out = bytearray()
        i = 0
        end = len(src) - plen
        cnt = 0
        while i <= end:
            match = True
            for j, tok in enumerate(tokens):
                if tok is not None and src[i+j] != tok:
                    match = False
                    break
            if match:
                out.extend(replace)
                i += plen
                cnt += 1
            else:
                out.append(src[i])
                i += 1
        if i < len(src):
            out.extend(src[i:])
        return bytes(out), cnt

    if sel:
        start, end = sel
        prefix = data[:start]
        body = data[start:end+1]
        suffix = data[end+1:]
        new_body, cnt = replace_body(body)
        # Αντικατάσταση του επιλεγμένου τμήματος
        state.set_bytes(start, new_body, replace_len=len(body))
    else:
        header = data[:64]
        body = data[64:]
        new_body, cnt = replace_body(body)
        # Αντικατάσταση από τη θέση 64 και μετά
        state.set_bytes(64, new_body, replace_len=len(body))

    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return cnt


def reverse_blocks(state, history=None, block_size: int = 1, **kwargs):
    if not getattr(state, 'current', None) or block_size <= 0:
        return 0
    sel = state.get_selection_range()
    before_all = bytes(state.current)
    if sel:
        start, end = sel
        if end < start:
            return 0
        data = state.current[start:end+1]
        new = bytearray()
        for i in range(0, len(data), block_size):
            block = data[i:i+block_size]
            new.extend(block[::-1])
        state.set_bytes(start, bytes(new), replace_len=len(data))
    else:
        header = state.current[:512]
        body = state.current[512:]
        new = bytearray()
        for i in range(0, len(body), block_size):
            block = body[i:i+block_size]
            new.extend(block[::-1])
        state.set_bytes(512, bytes(new), replace_len=len(body))
    after_all = bytes(state.current)
    if history is not None and hasattr(history, 'push') and before_all != after_all:
        history.push((0, before_all, after_all))
    return 1