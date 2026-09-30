import os
import asyncio
import shutil
import json
from utils.logger import logger

class VideoService:
    @staticmethod
    async def get_video_metadata(video_path: str) -> dict:
        """
        Uses ffprobe to extract duration, width, height from video.
        Falls back to default values if ffprobe is not installed or fails.
        """
        metadata = {"duration": 0, "width": 0, "height": 0}
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return metadata

        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "stream=width,height,duration:format=duration",
            "-of", "json",
            video_path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                data = json.loads(stdout.decode())
                # Extract format or stream duration
                duration = 0
                if "format" in data and "duration" in data["format"]:
                    duration = float(data["format"]["duration"])

                width, height = 0, 0
                if "streams" in data:
                    for stream in data["streams"]:
                        if "width" in stream and "height" in stream:
                            width = int(stream["width"])
                            height = int(stream["height"])
                            if duration == 0 and "duration" in stream:
                                duration = float(stream["duration"])
                            break

                metadata["duration"] = int(duration)
                metadata["width"] = width
                metadata["height"] = height
        except Exception as e:
            logger.error(f"Error probing video metadata: {e}")

        return metadata

    @staticmethod
    async def apply_thumbnail(input_video_path: str, thumbnail_path: str, output_video_path: str) -> bool:
        """
        Embeds / updates video thumbnail using ffmpeg while preserving audio and video quality (c:v copy, c:a copy).
        If ffmpeg is unavailable, safely falls back to using the original video file.
        """
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.warning("FFmpeg not found in system PATH. Copying original video without stream attachment.")
            shutil.copyfile(input_video_path, output_video_path)
            return True

        cmd = [
            ffmpeg,
            "-y",
            "-i", input_video_path,
            "-i", thumbnail_path,
            "-map", "0:v:0",
            "-map", "0:a?",
            "-map", "1:v:0",
            "-c:v:0", "copy",
            "-c:a", "copy",
            "-c:v:1", "mjpeg",
            "-disposition:v:1", "attached_pic",
            output_video_path
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                return True

            logger.warning(f"FFmpeg primary stream attach failed: {stderr.decode()}. Attempting fallback mode...")
            # Fallback FFmpeg command
            cmd_fallback = [
                ffmpeg,
                "-y",
                "-i", input_video_path,
                "-i", thumbnail_path,
                "-map", "0",
                "-map", "1",
                "-c", "copy",
                output_video_path
            ]
            proc_fb = await asyncio.create_subprocess_exec(
                *cmd_fallback,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr_fb = await proc_fb.communicate()
            if proc_fb.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                return True

            logger.warning(f"FFmpeg fallback failed: {stderr_fb.decode()}. Copying original video file.")
            shutil.copyfile(input_video_path, output_video_path)
            return True
        except Exception as e:
            logger.error(f"Error running FFmpeg: {e}")
            shutil.copyfile(input_video_path, output_video_path)
            return True
