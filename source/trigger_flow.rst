Trigger System Flow
===================

.. graphviz::

   digraph trigger {
       Event -> ConditionCheck
       ConditionCheck -> Reaction [label="if passed"]
       Reaction -> NextTrigger [label="optional"]
   }
