from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 60 * 8

    # Nearest-neighbor match threshold on face_recognition's Euclidean distance
    # between 128-d embeddings. Lower = stricter.
    # NOT YET CALIBRATED: 0.5 was an untested placeholder and produced a real
    # false accept in manual testing (an unenrolled person matched an
    # enrolled person at distance 0.455, sitting just under that threshold).
    # Tightened to 0.4 as an interim safety measure pending real calibration
    # against genuine/impostor distance data via evaluation/evaluate.py.
    face_match_threshold: float = 0.4

    # Eye Aspect Ratio below this value counts as "eyes closed" for a frame.
    # NOT YET CALIBRATED: a single static test photo (open eyes) measured
    # ~0.213 with this pipeline, below the textbook-typical 0.2-0.3 open-eye
    # range, likely because a single still photo differs from a live video
    # frame the landmark model was tuned against. This must be recalibrated
    # against real burst-capture video from enrolled participants before
    # being trusted; treat this value as a placeholder until then.
    ear_blink_threshold: float = 0.19

    # A kiosk burst capture must have at least this many frames with a
    # detected face before we attempt blink detection on it at all.
    liveness_min_valid_frames: int = 5

    # Minimum head-yaw range (degrees, approximate) across a capture burst
    # to count as natural movement -- an alternative passive liveness
    # signal alongside blink detection; either one passing is enough.
    # NOT YET CALIBRATED: no real burst data has been measured against
    # this yet, same caveat as ear_blink_threshold.
    head_yaw_min_range_degrees: float = 5.0

    # Frames are downscaled to at most this many pixels on the longer side
    # before running face detection during the liveness burst loop, which
    # runs detection repeatedly (once per frame). Speeds up each kiosk
    # attempt meaningfully at negligible accuracy cost, since EAR is a
    # ratio and scale-invariant. Does not affect the final match embedding,
    # which is computed on the full-resolution frame.
    # Lowered from 800 to 500 after real classroom use showed the 3-step
    # challenge sequence taking too long: measured full per-frame cost
    # (detection + landmarks) was ~910ms at 800px vs ~304ms at 500px, a
    # real ~3x speedup, with the same test image still correctly detected
    # at 500px. Needs live confirmation it doesn't hurt detection reliability
    # at odd real-world angles/distances, same caveat as the other
    # not-yet-fully-calibrated values above.
    liveness_detection_max_dimension: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
