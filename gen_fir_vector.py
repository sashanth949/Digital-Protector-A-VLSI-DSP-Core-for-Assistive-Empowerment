"""FIR golden model + test-vector generator (4-bit in, 4-bit coeff, 8 taps).

Run:  python fir_golden.py
Writes the same .mem files your testbenches already use.
"""
import csv
import os
import numpy as np
from scipy import signal

# ------------------------------------------------------------------ config
IN_BITS, COEF_BITS, NUM_TAPS = 4, 4, 8
OUT_BITS = 12            # fir_filter sample_out width
DSP_BITS = 8             # width of dsp_input after the FIR (saturating)
FS = 8000
FC = 2000                # cutoff. 3400 Hz is too close to Nyquist for 8 taps
TONE_HZ, NOISE_HZ = 500, 3800
GAIN_VALUE = 0           # gain = 1 + g/16
RTL_LATENCY = 0          # cycles between model output and Enhanced_Out in the CSV


def srange(bits):
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1

IN_MIN, IN_MAX = srange(IN_BITS)
CO_MIN, CO_MAX = srange(COEF_BITS)
IN_ABS = max(abs(IN_MIN), IN_MAX)
ACC_BITS = IN_BITS + COEF_BITS + int(np.ceil(np.log2(NUM_TAPS)))   # 11


# ------------------------------------------------------------------ helpers
def to_hex(val, bits):
    val = int(val)
    lo, hi = srange(bits)
    assert lo <= val <= hi, f"{val} does not fit {bits}b"
    return f"{val & ((1 << bits) - 1):0{(bits + 3) // 4}X}"


def export_mem(name, data, bits):
    with open(name, "w") as f:
        f.writelines(to_hex(v, bits) + "\n" for v in data)


def sat(x, bits):
    lo, hi = srange(bits)
    return max(lo, min(hi, int(x)))


# ------------------------------------------------------------- hardware model
def fir_model(x, taps):
    """Bit-exact FIR, full-precision accumulate, zero state at reset.
    y[i] = sum_k taps[k] * x[i-k]   (k=0 is the newest sample, as in the RTL)."""
    x = np.asarray(x, dtype=np.int64)
    return np.convolve(x, np.asarray(taps, dtype=np.int64))[:len(x)]


def fir_model_slow(x, taps):
    """Literal loop version, used only to cross-check fir_model."""
    return np.array([sum(int(taps[k]) * int(x[i - k])
                         for k in range(len(taps)) if i - k >= 0)
                     for i in range(len(x))], dtype=np.int64)


def gain_model(a, g):
    """ALU GAIN op: round(a * (16+g) / 16) with arithmetic shift."""
    return (int(a) * (16 + int(g)) + 8) >> 4


def chain_model(x, taps, g):
    """FIR -> sat to 8b (dsp_input) -> GAIN -> 16b enhanced_out."""
    dsp_in = [sat(v, DSP_BITS) for v in fir_model(x, taps)]
    return np.array([gain_model(v, g) for v in dsp_in], dtype=np.int64)


# ------------------------------------------------------------ coefficient design
def worst_case(taps):
    return int(np.sum(np.abs(taps))) * IN_ABS


def design_taps():
    """Window-method design, then pick the integer scale that gives the best
    500 Hz vs 3800 Hz selectivity while guaranteeing the FIR output can never
    saturate the 8-bit dsp_input and the accumulator never overflows."""
    taps_f = signal.firwin(NUM_TAPS, FC, fs=FS, window="hamming")
    taps_f = taps_f / taps_f.sum()                       # unity DC gain
    dsp_max = srange(DSP_BITS)[1]
    best = None
    for scale in range(2, 33):
        q = np.clip(np.round(taps_f * scale), CO_MIN, CO_MAX).astype(np.int32)
        if q.sum() <= 0 or worst_case(q) > dsp_max:
            continue
        _, h = signal.freqz(q, worN=[TONE_HZ, NOISE_HZ], fs=FS)
        g = np.abs(h)
        score = 20 * np.log10(g[0] / max(g[1], 1e-9))   # selectivity in dB
        if best is None or score > best[0] + 1e-9:
            best = (score, scale, q)
    assert best is not None, "no coefficient set satisfies the range limits"
    return taps_f, best[2], best[1]


def response_db(taps, freqs):
    _, h = signal.freqz(taps, worN=freqs, fs=FS)
    return 20 * np.log10(np.maximum(np.abs(h), 1e-9))


# ------------------------------------------------------------------ SNR
def snr_db_aligned(ref, test, max_shift=NUM_TAPS, skip=NUM_TAPS):
    """Best-fit-gain SNR over a small delay search; skips the start-up transient."""
    ref = np.asarray(ref, float)
    test = np.asarray(test, float)
    best = -np.inf
    for s in range(max_shift):
        r = ref[:len(ref) - s][skip:]
        q = test[s:][skip:]
        qq = np.dot(q, q)
        if qq == 0:
            continue
        a = np.dot(r, q) / qq
        noise = np.sum((r - a * q) ** 2)
        best = max(best, 10 * np.log10(np.sum(r ** 2) / max(noise, 1e-12)))
    return best


# ------------------------------------------------------------------ stimuli
def make_speech_like(n=400, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FS
    clean = 0.6 * np.sin(2 * np.pi * TONE_HZ * t)
    noisy = clean + 0.3 * np.sin(2 * np.pi * NOISE_HZ * t) + 0.1 * rng.normal(size=n)
    noisy /= np.max(np.abs(noisy))
    x = np.clip(np.round(noisy * IN_MAX), IN_MIN, IN_MAX).astype(np.int32)
    return clean, x


def make_corner_vectors(n=400, seed=7):
    rng = np.random.default_rng(seed)
    v = [0] * 20
    v += [IN_MAX] + [0] * 19
    v += [IN_MIN] + [0] * 19
    v += [IN_MAX] * 40 + [IN_MIN] * 40
    v += [IN_MAX, IN_MIN] * 20 + [IN_MIN, IN_MAX] * 20
    v += [0] * 10
    v += rng.integers(IN_MIN, IN_MAX + 1, size=max(0, n - len(v))).tolist()
    return np.array(v[:n], dtype=np.int32)


# ------------------------------------------------------------------ main
def main():
    clean, x = make_speech_like()
    taps_f, taps, scale = design_taps()

    # model self-check
    probe = np.random.default_rng(1).integers(IN_MIN, IN_MAX + 1, 200)
    assert np.array_equal(fir_model(probe, taps), fir_model_slow(probe, taps))

    freqs = [TONE_HZ, NOISE_HZ]
    print("float taps :", np.round(taps_f, 4))
    print("int taps   :", taps, f"(scale {scale}, DC gain {taps.sum()})")
    print("zero taps  :", int(np.sum(taps == 0)), "of", NUM_TAPS)
    print("response   : float @500/3800 Hz =",
          np.round(response_db(taps_f, freqs), 2), "dB")
    print("             int   @500/3800 Hz =",
          np.round(response_db(taps, freqs) - 20 * np.log10(taps.sum()), 2),
          "dB (normalised to DC)")
    w = worst_case(taps)
    print(f"worst-case |acc| = {w}; fits {ACC_BITS}b acc: {w < 1 << (ACC_BITS - 1)}; "
          f"fits {OUT_BITS}b out: {w <= srange(OUT_BITS)[1]}; "
          f"fits {DSP_BITS}b dsp_input: {w <= srange(DSP_BITS)[1]}")

    fir = fir_model(x, taps)
    chain = chain_model(x, taps, GAIN_VALUE)

    before = snr_db_aligned(clean, x.astype(float))
    after = snr_db_aligned(clean, fir.astype(float))
    print(f"\nSNR before (4-bit input) : {before:6.2f} dB")
    print(f"SNR after  (FIR model)   : {after:6.2f} dB")
    print(f"improvement              : {after - before:6.2f} dB")

    csv_name = "NoiseSlayer_Verification.csv"
    if os.path.exists(csv_name):
        with open(csv_name) as f:
            rtl = np.array([int(r["Enhanced_Out"]) for r in csv.DictReader(f)], float)
        ref = chain[:len(rtl) - RTL_LATENCY]
        rtl_al = rtl[RTL_LATENCY:RTL_LATENCY + len(ref)]
        print(f"SNR after  (RTL CSV)     : {snr_db_aligned(clean, rtl_al):6.2f} dB")
        print("RTL vs model mismatches  :", int(np.sum(rtl_al != ref[:len(rtl_al)])))

    export_mem("coefficients.mem", taps, COEF_BITS)
    export_mem("input_audio.mem", x, IN_BITS)
    export_mem("golden_output.mem", fir, OUT_BITS)
    export_mem(f"golden_chain_g{GAIN_VALUE}.mem", chain, 16)

    xc = make_corner_vectors()
    export_mem("input_corner.mem", xc, IN_BITS)
    export_mem("golden_corner_fir.mem", fir_model(xc, taps), OUT_BITS)
    for g in (0, 16, 255):
        export_mem(f"golden_corner_chain_g{g}.mem", chain_model(xc, taps, g), 16)
    print("\nWrote coefficients/input/golden .mem files (normal + corner).")


if __name__ == "__main__":
    main()
