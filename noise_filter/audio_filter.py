import numpy as np


class AudioFilter:
    """Real-time DSP audio filter for noise suppression and gain control."""

    def __init__(self, target_gain_dB: float = 0.0, noise_gate_threshold: float = 0.005):
        self.target_gain_dB = target_gain_dB
        self.noise_gate_threshold = noise_gate_threshold

    def process(self, pcm_bytes: bytes) -> bytes:
        """Apply noise gate and DC offset removal on 16-bit PCM audio frame."""
        if not pcm_bytes:
            return b""

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return pcm_bytes

        # Remove DC offset (zero-center)
        samples = samples - np.mean(samples)

        # Noise gate: zero out low amplitude background static
        max_amplitude = np.max(np.abs(samples))
        if max_amplitude < self.noise_gate_threshold * 32768.0:
            return b"\x00" * len(pcm_bytes)

        # Soft clipping protection
        np.clip(samples, -32768.0, 32767.0, out=samples)
        return samples.astype(np.int16).tobytes()
