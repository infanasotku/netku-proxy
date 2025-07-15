from abc import ABC, abstractmethod
from uuid import UUID


class UUIDMismatchError(Exception):
    """
    Raised when the UUID received after restarting the engine does not match the expected UUID.

    Attributes:
        expected (UUID): The UUID that was originally sent with the restart request.
        received (UUID): The UUID that was received after the engine restarted.
    """

    def __init__(self, expected: UUID, received: UUID):
        super().__init__(f"Expected UUID {expected}, but received {received}.")
        self.expected = expected
        self.received = received


class EngineManager(ABC):
    @abstractmethod
    async def restart(self, uuid: UUID, *, addr: str):
        """
        Request a restart of the proxy engine and wait until it completes.

        This method sends a restart request to the engine, which will be restarted with the provided UUID as an access key.
        It blocks until the engine finishes restarting and responds with its new identity. If the returned UUID does not match the one originally
        sent, a UUIDMismatchError is raised.

        Args:
            uuid (UUID): The access key the engine will be restarted with. Users will connect to the engine using this key.
            addr (str): The address of the engine to restart, in 'host:port' format.

        Raises:
            UUIDMismatchError: If the UUID returned after restart does not match the expected one.
        """
