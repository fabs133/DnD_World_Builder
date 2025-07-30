Trigger Chain (Mermaid)
=======================

.. mermaid::

   graph TD
       Event -->|passes| Condition
       Condition -->|true| Reaction
       Reaction -->|triggers| NextTrigger
