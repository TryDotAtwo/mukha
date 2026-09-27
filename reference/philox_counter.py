"""Independent CPU oracle for the pinned CUDA Philox4x32-10 counter mapping."""

MASK32 = (1 << 32) - 1
M0 = 0xD2511F53
M1 = 0xCD9E8D57
W0 = 0x9E3779B9
W1 = 0xBB67AE85


def uniform_bits(word: int) -> int:
    """Pinned cuRAND 13.1 `_curand_uniform` FP32 result, with FMA disabled."""
    import struct

    if not 0 <= word < 1 << 32:
        raise ValueError('word must fit uint32')

    def f32(value: float) -> float:
        return struct.unpack('<f', struct.pack('<f', value))[0]

    scale = f32(2.3283064e-10)
    half = f32(scale / 2.0)
    result = f32(f32(f32(float(word)) * scale) + half)
    return struct.unpack('<I', struct.pack('<f', result))[0]


def words(seed: int, entity_id: int, tick: int, draw_block: int) -> tuple[int, int, int, int]:
    if not 0 <= seed < 1 << 64:
        raise ValueError('seed must fit uint64')
    if not 0 <= entity_id < 1 << 32:
        raise ValueError('entity_id must fit uint32')
    if not 0 <= tick < 1 << 64:
        raise ValueError('tick must fit uint64')
    if not 0 <= draw_block < 1 << 32:
        raise ValueError('draw_block must fit uint32')
    c0, c1, c2, c3 = entity_id, tick & MASK32, tick >> 32, draw_block
    k0, k1 = seed & MASK32, seed >> 32
    for round_id in range(10):
        p0, p1 = M0 * c0, M1 * c2
        c0, c1, c2, c3 = ((p1 >> 32) ^ c1 ^ k0) & MASK32, p1 & MASK32, \
                         ((p0 >> 32) ^ c3 ^ k1) & MASK32, p0 & MASK32
        if round_id != 9:
            k0 = (k0 + W0) & MASK32
            k1 = (k1 + W1) & MASK32
    return c0, c1, c2, c3


def draw(seed: int, entity_id: int, tick: int, draw_index: int) -> int:
    if not 0 <= draw_index < 1 << 34:
        raise ValueError('draw index exceeds 32-bit block capacity')
    return words(seed, entity_id, tick, draw_index >> 2)[draw_index & 3]
