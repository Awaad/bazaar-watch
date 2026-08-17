"""Signals, review tasks, leases, responses, trust computation.

Owns its own tables. Other modules reach it only through `service.py`, never by
importing `models.py`. See docs/15-repo-structure-standards.md section 2.
"""
