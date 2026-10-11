# Planning methodology

This is planning guidance, not official AQI or activity clearance. Concentrations retain source/time/unit. The current engine selects measured station evidence when available; IDW estimates weight nearby stations by distance. A CAMS model is identified as regional, not treated as a colocated station.

Age-group/caution boundaries come from guardian_rules.py. Worse raw flags remain visible immediately; recovery requires consecutive hourly observations (default two). Duplicate refreshes in one hour do not count twice; missing hours break recovery. A three-observation mean is supporting context, never a replacement concentration. FLAG_ESCALATION_HOURS and FLAG_RECOVERY_HOURS configure alert persistence.

Cleaner windows integrate each forecast interval across the whole activity duration. Missing coverage or stale source data produces no suggestion. Comparisons use the same school-local day and school hours and still require timetable/room review.

Outdoor minutes are the timetable duration of outdoor orange/red blocks, compared with suggested indoor alternatives. They are not measured exposure reduction or improved health. Indoor air remains unknown without a usable fresh sensor; AC alone does not establish clean air.

Translations use assets/catalogue.json for UI phrases/action codes and server notifications. hi/mr need native review. Published school-authored wording is preserved. Unknown UI keys use English with development warnings containing opaque identifiers only.
