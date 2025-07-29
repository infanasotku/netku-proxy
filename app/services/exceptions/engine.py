from uuid import UUID


class EngineNotExistError(KeyError):
    def __init__(self, id: UUID, message: str | None = None) -> None:
        if message is None:
            message = f"Engine with ID {id} does not exist."
        super().__init__(message)
        self.id = id

    def __str__(self) -> str:
        return str(self.args[0])


class EngineDeadError(ValueError):
    def __init__(self, id: UUID, message: str | None = None) -> None:
        if message is None:
            message = f"Cannot restart engine with ID {id}: engine is DEAD."
        super().__init__(message)
        self.id = id
