"""Channel-agnostic actor authorization guard."""


class UnauthorizedActorError(PermissionError):
    """Raised when an action is attempted by a non-owner actor."""


class OwnerGuard:
    """Guards callbacks and approvals against unauthorized actors."""

    def __init__(self, owner_id: str) -> None:
        self.owner_id = str(owner_id)

    def verify_actor(self, actor_id: str) -> bool:
        """Verify that actor matches owner. Fails closed."""
        if str(actor_id) != self.owner_id:
            msg = (
                f"Actor {actor_id} is not authorized "
                f"(expected {self.owner_id})"
            )
            raise UnauthorizedActorError(msg)
        return True
