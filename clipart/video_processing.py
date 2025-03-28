import os
import traceback
from typing import List, Tuple
import cv2  # opencv-python
import numpy as np
from PIL import Image

# Import configuration and utilities using relative imports
from . import config
from . import utils


def create_video_mockup(
    image_paths: List[str],
    output_path: str,
    target_size: Tuple[int, int] = config.VIDEO_TARGET_SIZE,
    fps: int = config.VIDEO_FPS,
    num_transition_frames: int = config.VIDEO_TRANSITION_FRAMES,
    display_frames: int = config.VIDEO_DISPLAY_FRAMES,
) -> None:
    """Creates an MP4 video showcasing images with transitions."""
    if not image_paths:
        print("No image paths provided for video creation.")
        return

    cv2_images = []
    pad_color_bgr = (255, 255, 255)

    print(f"Processing {len(image_paths)} images for video...")
    for i, img_path in enumerate(image_paths):
        try:
            pil_img = utils.safe_load_image(img_path, "RGBA")
            if pil_img is None:
                print(f"Warn: Skipping invalid image {img_path}")
                continue

            if pil_img.mode == "RGBA":
                bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                bg.paste(pil_img, (0, 0), pil_img)
                pil_img_rgb = bg
            elif pil_img.mode != "RGB":
                pil_img_rgb = pil_img.convert("RGB")
            else:
                pil_img_rgb = pil_img

            img_cv_bgr = cv2.cvtColor(np.array(pil_img_rgb), cv2.COLOR_RGB2BGR)
            h, w = img_cv_bgr.shape[:2]
            if h <= 0 or w <= 0:
                print(f"Warn: Invalid dimensions ({w}x{h}) for image {img_path}")
                continue

            target_w, target_h = target_size
            aspect = w / h
            target_aspect = target_w / max(1, target_h)  # Avoid div by zero
            if aspect > target_aspect:
                new_w, new_h = target_w, max(1, int(target_w / aspect))
            else:
                new_h, new_w = target_h, max(1, int(target_h * aspect))

            resized = cv2.resize(
                img_cv_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4
            )

            pad_y_total, pad_x_total = max(0, target_h - new_h), max(
                0, target_w - new_w
            )
            pad_y_t, pad_y_b = pad_y_total // 2, pad_y_total - (pad_y_total // 2)
            pad_x_l, pad_x_r = pad_x_total // 2, pad_x_total - (pad_x_total // 2)

            padded = cv2.copyMakeBorder(
                resized,
                pad_y_t,
                pad_y_b,
                pad_x_l,
                pad_x_r,
                cv2.BORDER_CONSTANT,
                value=pad_color_bgr,
            )

            # Final resize interpolation choice
            if padded.shape[0] > target_h or padded.shape[1] > target_w:
                interpolation = cv2.INTER_AREA
            elif padded.shape[0] < target_h or padded.shape[1] < target_w:
                interpolation = cv2.INTER_LANCZOS4
            else:
                interpolation = cv2.INTER_NEAREST

            final_frame = cv2.resize(padded, target_size, interpolation=interpolation)
            cv2_images.append(final_frame)

        except Exception as e:
            print(f"Error processing image {img_path} for video: {e}")
            traceback.print_exc()

    if not cv2_images:
        print("Error: No valid frames processed for video.")
        return

    print(f"Writing {len(cv2_images)} unique frames to video...")
    try:
        codecs = ["mp4v", "avc1", "h264", "xvid"]
        out = None
        for c in codecs:
            fourcc = cv2.VideoWriter_fourcc(*c)
            out = cv2.VideoWriter(output_path, fourcc, float(fps), target_size)
            if out.isOpened():
                print(f"Using codec: {c}")
                break
            else:
                print(f"Codec {c} failed...")
                out = None

        if not out or not out.isOpened():
            print("Trying platform default codec (0)...")
            out = cv2.VideoWriter(output_path, 0, float(fps), target_size)
            if not out.isOpened():
                print("Error: Could not open video writer.")
                return
            else:
                print("Using platform default codec.")
    except Exception as e:
        print(f"Error initializing video writer: {e}")
        return

    num_img = len(cv2_images)
    for i in range(num_img):
        for _ in range(display_frames):
            out.write(cv2_images[i])
        if i < num_img - 1 and num_transition_frames > 0:
            curr_f, next_f = cv2_images[i], cv2_images[i + 1]
            if curr_f.shape != next_f.shape or curr_f.dtype != next_f.dtype:
                print(f"Warn: Frame shape/type mismatch. Transition {i} abrupt.")
                for _ in range(num_transition_frames):
                    out.write(next_f)
                continue
            for j in range(1, num_transition_frames + 1):
                alpha = j / float(num_transition_frames)
                try:
                    blended = cv2.addWeighted(curr_f, 1.0 - alpha, next_f, alpha, 0)
                    out.write(blended)
                except Exception as e:
                    print(
                        f"Error blending frame {j}/{num_transition_frames} (transition {i}): {e}. Writing next frame."
                    )
                    out.write(next_f)  # Fallback

    if num_img == 1:  # Ensure single image gets displayed properly
        for _ in range(display_frames):
            out.write(cv2_images[0])

    out.release()
    # Check file size after release
    final_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    if final_size > 0:
        print(f"Video saved successfully to {output_path} ({final_size / 1024:.1f} KB)")
    else:
        print(f"Error: Video file {output_path} is empty or was not created.")
