from PyQt5.QtWidgets import QGraphicsItem

class BaseTileItem(QGraphicsItem):
    """
    Base class for tile items in the DnDProject.

    Attributes
    ----------
    attributes : dict
        Dictionary to store custom attributes for the tile item.
    event_emitter : object or None
        External event emitter, to be set externally.
    """

    def __init__(self):
        """
        Initialize the BaseTileItem.
        """
        super().__init__()
        self.attributes = {}
        self.event_emitter = None  # Will be set externally

    def handle_hover_enter(self, event):
        """
        Handle the hover enter event.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement handle_hover_enter.")

    def handle_hover_leave(self, event):
        """
        Handle the hover leave event.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement handle_hover_leave.")

    def handle_right_click(self, event):
        """
        Handle the right click event.

        Parameters
        ----------
        event : QGraphicsSceneMouseEvent
            The mouse event.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement handle_right_click.")
