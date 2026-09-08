# Tag Model

A Tag has ID, path, type, unit, quality, timestamp, source device, update policy, retention class, safety classification, and read/write policy. Definitions belong to Tag Registry; live values belong to the Data Plane.

Writes MUST pass type, range, quality, permission, and mode checks. Safety/control tags require explicit runtime authorization and cannot be changed by AI directly.

