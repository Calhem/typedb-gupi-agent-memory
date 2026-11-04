"""Selectable candidate extractors, by version (docs/formation/rules-v2.1.md).

    from gupi.formation import extractors
    extractors.get("rules:v2.1").extract(observation)

`rules:v2` is kept exactly as it was, so earlier results can be reproduced. Nothing here changes which
extractor any existing caller uses: callers name the version they want.
"""

from gupi.formation.rules_v2 import RulesV2
from gupi.formation.rules_v21 import RulesV21

VERSIONS = {"rules:v2": RulesV2, "rules:v2.1": RulesV21}


def get(version):
    """A new extractor of that version. KeyError for an unknown version."""
    return VERSIONS[version]()
