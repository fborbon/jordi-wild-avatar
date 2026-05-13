"""
Real-time 2D face animator using dlib 68-point face landmarks.
Drives mouth open/close from audio amplitude, eye blinks, subtle head bob.
Runs fully on CPU at ~30fps.

dlib 68-point landmark map:
  Mouth outer:  48-59
  Mouth inner:  60-67  (60=left, 64=top, 62=bottom-ish, 66=bottom-center)
  Left eye:     36-41
  Right eye:    42-47
  Nose:         27-35
"""

import os, time, urllib.request
import cv2
import dlib
import numpy as np

# ── dlib landmark indices ──────────────────────────────────────────────────────
MOUTH_OUTER  = list(range(48, 60))
MOUTH_INNER  = list(range(60, 68))
MOUTH_TOP    = 51   # top center of inner mouth
MOUTH_BOT    = 57   # bottom center of inner mouth
MOUTH_LEFT   = 48
MOUTH_RIGHT  = 54
L_EYE        = list(range(36, 42))
R_EYE        = list(range(42, 48))
L_EYE_TOP    = [37, 38]
L_EYE_BOT    = [41, 40]
R_EYE_TOP    = [43, 44]
R_EYE_BOT    = [47, 46]

# Shape predictor model URL (dlib's official 68-point model)
MODEL_URL  = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
MODEL_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_BZ2  = os.path.join(MODEL_DIR, "shape_predictor_68_face_landmarks.dat.bz2")
MODEL_DAT  = os.path.join(MODEL_DIR, "shape_predictor_68_face_landmarks.dat")


def ensure_model():
    if os.path.exists(MODEL_DAT):
        return
    import bz2
    print("Downloading dlib face landmark model (~100MB)...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    urllib.request.urlretrieve(MODEL_URL, MODEL_BZ2)
    print("Decompressing...")
    with bz2.open(MODEL_BZ2, "rb") as f_in, open(MODEL_DAT, "wb") as f_out:
        f_out.write(f_in.read())
    os.remove(MODEL_BZ2)
    print("Model ready.")


class FaceAnimator:
    def __init__(self, image_bgr: np.ndarray, size: int = 300):
        """
        image_bgr : numpy BGR image containing a face
        size      : output square size (smaller = faster, 250-350 is ideal)
        """
        self.size = size
        ensure_model()

        detector  = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(MODEL_DAT)

        # Work at output size for efficiency
        base = cv2.resize(image_bgr, (size, size))
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

        faces = detector(gray, 1)
        if not faces:
            # Try with upsampling
            faces = detector(gray, 2)
        if not faces:
            raise ValueError("No face detected. Use a clear, front-facing photo.")

        shape     = predictor(gray, faces[0])
        self.pts  = np.array([[shape.part(i).x, shape.part(i).y]
                               for i in range(68)], dtype=np.float32)
        self.base = base.copy()
        h, w      = size, size

        # ── Mouth region ──────────────────────────────────────────────────
        m_pts       = self.pts[MOUTH_OUTER + MOUTH_INNER]
        pad         = 10
        mx1         = max(0, int(m_pts[:, 0].min()) - pad)
        my1         = max(0, int(m_pts[:, 1].min()) - pad)
        mx2         = min(w, int(m_pts[:, 0].max()) + pad)
        my2         = min(h, int(m_pts[:, 1].max()) + pad)
        self.m_box  = (mx1, my1, mx2, my2)
        # Natural closed mid-line: halfway between inner top and bottom
        self.m_mid  = int((self.pts[MOUTH_TOP][1] + self.pts[MOUTH_BOT][1]) / 2)
        # Max gap in pixels when fully open
        self.m_max  = max(4, int((my2 - my1) * 0.38))

        # ── Eye regions ───────────────────────────────────────────────────
        def _eye_box(idxs):
            ep  = self.pts[idxs]
            x1  = max(0, int(ep[:, 0].min()) - 5)
            y1  = max(0, int(ep[:, 1].min()) - 4)
            x2  = min(w, int(ep[:, 0].max()) + 5)
            y2  = min(h, int(ep[:, 1].max()) + 4)
            return (x1, y1, x2, y2)

        self.l_eye_box = _eye_box(L_EYE)
        self.r_eye_box = _eye_box(R_EYE)

        # Skin color sampled from cheek (below left eye)
        cx = int(self.pts[1][0])
        cy = int(self.pts[1][1])
        self.skin = tuple(int(v) for v in base[np.clip(cy, 0, h-1), np.clip(cx, 0, w-1)])

        # ── Animation state ───────────────────────────────────────────────
        self.smooth_amp = 0.0
        self.head_phase = 0.0
        self.next_blink = time.time() + np.random.uniform(1.5, 4.0)
        self.blink_t    = None
        self.BLINK_DUR  = 0.13

    # ── Private helpers ───────────────────────────────────────────────────────

    def _open_mouth(self, frame: np.ndarray, amount: float) -> np.ndarray:
        gap = int(amount * self.m_max)
        if gap < 1:
            return frame
        mx1, my1, mx2, my2 = self.m_box
        mid    = self.m_mid
        result = frame.copy()

        # Shift upper half of mouth region upward
        upper    = frame[my1:mid, mx1:mx2].copy()
        new_my1  = max(0, my1 - gap)
        uh       = mid - my1
        result[new_my1:new_my1 + uh, mx1:mx2] = upper

        # Shift lower half downward
        lower    = frame[mid:my2, mx1:mx2].copy()
        new_my2  = min(frame.shape[0], my2 + gap)
        lh       = my2 - mid
        result[new_my2 - lh:new_my2, mx1:mx2] = lower

        # Fill gap with dark interior
        g_top = max(0, new_my1 + uh)
        g_bot = min(frame.shape[0], new_my2 - lh)
        g_h   = max(0, g_bot - g_top)
        g_w   = mx2 - mx1
        if g_h > 0 and g_w > 0:
            interior       = np.zeros((g_h, g_w, 3), dtype=np.uint8)
            interior[:, :] = (12, 6, 6)
            fade = max(1, min(4, g_h // 2))
            alpha = np.ones((g_h, g_w), dtype=np.float32)
            for i in range(fade):
                a = (i + 1) / (fade + 1)
                alpha[i, :]      *= a
                alpha[-(i+1), :] *= a
            for c in range(3):
                result[g_top:g_bot, mx1:mx2, c] = (
                    interior[:, :, c] * alpha +
                    result[g_top:g_bot, mx1:mx2, c] * (1.0 - alpha)
                ).astype(np.uint8)

        # Feather blend the whole mouth zone
        msk = np.zeros(frame.shape[:2], dtype=np.float32)
        msk[max(0, my1-gap):min(frame.shape[0], my2+gap), mx1:mx2] = amount * 0.85
        msk = cv2.GaussianBlur(msk, (11, 11), 0)
        for c in range(3):
            result[:, :, c] = (
                result[:, :, c] * msk + frame[:, :, c] * (1.0 - msk)
            ).astype(np.uint8)

        return result

    def _blink(self, frame: np.ndarray, amount: float) -> np.ndarray:
        if amount < 0.02:
            return frame
        result = frame.copy()
        for (x1, y1, x2, y2) in [self.l_eye_box, self.r_eye_box]:
            eye_h  = y2 - y1
            lid_h  = max(1, int(eye_h * amount))
            overlay = result.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y1 + lid_h), self.skin, -1)
            cv2.GaussianBlur(overlay[y1:y2, x1:x2],
                             (5, 5), 0,
                             overlay[y1:y2, x1:x2])
            result = cv2.addWeighted(result, 1 - amount * 0.8,
                                     overlay, amount * 0.8, 0)
        return result

    # ── Public ────────────────────────────────────────────────────────────────

    def get_frame(self, amplitude: float, dt: float) -> np.ndarray:
        """Return animated BGR numpy frame. Call at ~30fps."""
        now = time.time()

        # Smooth amplitude
        self.smooth_amp = self.smooth_amp * 0.55 + amplitude * 0.45

        # Head bob: tiny rotation + horizontal sway
        self.head_phase += dt * 0.9
        angle = float(np.sin(self.head_phase) * 0.6)
        tx    = float(np.sin(self.head_phase * 0.55) * 2.5)
        M = cv2.getRotationMatrix2D((self.size // 2, self.size // 2), angle, 1.0)
        M[0, 2] += tx
        frame = cv2.warpAffine(self.base, M, (self.size, self.size),
                               flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)

        # Blink
        blink_amt = 0.0
        if self.blink_t is None and now >= self.next_blink:
            self.blink_t = now
        if self.blink_t is not None:
            prog = (now - self.blink_t) / self.BLINK_DUR
            if prog < 1.0:
                blink_amt = float(np.sin(prog * np.pi))
            else:
                self.blink_t    = None
                self.next_blink = now + np.random.uniform(2.0, 6.0)
        frame = self._blink(frame, blink_amt)

        # Mouth
        frame = self._open_mouth(frame, self.smooth_amp)

        return frame

    @staticmethod
    def bgr_to_pygame(frame_bgr):
        import pygame
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
