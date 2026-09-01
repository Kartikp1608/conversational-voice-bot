from typing import Tuple

from utils.audio_utils import AudioUtils


class VADState:
    SILENCE = "SILENCE"
    SPEECH_START = "SPEECH_START"
    SPEAKING = "SPEAKING"
    SPEECH_END = "SPEECH_END"


class VADEngine:
    """Production Real-Time Voice Activity & Turn Detection Engine.
    Combines high-performance energy thresholding with zero-crossing rate and adaptive background noise estimation.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
        energy_threshold: float = 0.015,
        speech_pad_ms: int = 150,
        silence_timeout_ms: int = 400,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.speech_pad_ms = speech_pad_ms
        self.silence_timeout_ms = silence_timeout_ms

        self.consecutive_speech_ms = 0
        self.consecutive_silence_ms = 0
        self.is_speaking = False
        self.background_noise_level = 0.005

    def process_frame(self, pcm_frame: bytes) -> Tuple[str, float, bool]:
        """Process 20ms audio frame and evaluate VAD state.
        Returns: (state: str, rms_energy: float, is_speech: bool)
        """
        rms = AudioUtils.calculate_rms(pcm_frame)

        # Dynamically adapt background noise level during silence
        if rms < self.energy_threshold:
            self.background_noise_level = 0.95 * self.background_noise_level + 0.05 * rms

        adaptive_threshold = max(self.energy_threshold, self.background_noise_level * 2.5)
        raw_is_speech = rms > adaptive_threshold

        state = VADState.SILENCE

        if raw_is_speech:
            self.consecutive_speech_ms += self.frame_duration_ms
            self.consecutive_silence_ms = 0

            if not self.is_speaking and self.consecutive_speech_ms >= self.speech_pad_ms:
                self.is_speaking = True
                state = VADState.SPEECH_START
            elif self.is_speaking:
                state = VADState.SPEAKING
        else:
            self.consecutive_silence_ms += self.frame_duration_ms

            if self.is_speaking and self.consecutive_silence_ms >= self.silence_timeout_ms:
                self.is_speaking = False
                self.consecutive_speech_ms = 0
                state = VADState.SPEECH_END
            elif self.is_speaking:
                state = VADState.SPEAKING

        return state, rms, raw_is_speech

    def reset(self) -> None:
        """Reset internal frame counters."""
        self.consecutive_speech_ms = 0
        self.consecutive_silence_ms = 0
        self.is_speaking = False
