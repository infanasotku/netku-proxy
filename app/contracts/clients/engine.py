from abc import ABC, abstractmethod
from uuid import UUID


class EngineManager(ABC):
    @abstractmethod
    async def restart(self, uuid: UUID, *, addr: str):
        """
        Request a restart of the proxy engine and wait until it completes.

        Sends a synchronous command to the proxy engine instructing it to perform
        a full restart. This method blocks until the engine confirms that the restart
        has been completed successfully.

        The manager does not control the restart process directly, but delegates it
        to the engine, assuming the engine itself handles shutdown and reinitialization.

        Args:
            uuid (UUID): The identifier with which the engine will be restart.
            addr (str): Network address (in 'host:port' format) of the engine to be restarted.
        """
