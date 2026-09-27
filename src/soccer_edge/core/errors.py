"""Exception hierarchy. Fail loudly; never degrade silently."""


class SoccerEdgeError(Exception):
    """Base class."""


class IdentityError(SoccerEdgeError):
    """Identity resolution failed (unknown or ambiguous)."""


class AmbiguousAliasError(IdentityError):
    """An alias maps to more than one canonical entity in the requested scope."""


class UnknownAliasError(IdentityError):
    """An alias maps to no canonical entity."""


class DiscoveryIncompleteError(SoccerEdgeError):
    """Kalshi discovery could not prove completeness; results must not be used as a catalog."""


class CoverageInvariantError(SoccerEdgeError):
    """unaccounted_contracts != 0 or another accounting invariant was violated."""


class FeeMechanicsUnverifiedError(SoccerEdgeError):
    """Fee regime for a contract could not be verified; fail closed."""


class CoherenceError(SoccerEdgeError):
    """Priced probabilities violate a logical implication or sum constraint."""


class ArchiveImmutabilityError(SoccerEdgeError):
    """Attempt to overwrite or mutate an archived prediction."""


class FreshnessError(SoccerEdgeError):
    """Inputs are staler than the allowed gate."""


class ProviderError(SoccerEdgeError):
    """External data provider failed or returned an unusable payload."""
