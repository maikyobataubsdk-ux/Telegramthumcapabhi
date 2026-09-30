class CaptionService:
    @staticmethod
    def validate_caption(caption_text: str) -> bool:
        """Validates caption text against Telegram 1024 char limit for media captions."""
        if not caption_text or len(caption_text) > 1024:
            return False
        return True

    @staticmethod
    def format_caption(caption_text: str) -> str:
        """Sanitizes or formats caption string."""
        return caption_text.strip() if caption_text else ""
