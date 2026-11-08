class ApiError(Exception):
    """Errore dell'API: diventa `{"error": "..."}` con lo status indicato."""

    def __init__(self, text: str, status: int = 400):
        super().__init__(text)
        self.text, self.status = text, status
