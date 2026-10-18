import sys, re
from functools import cmp_to_key
from typing import List, Tuple, Optional

sys.dont_write_bytecode = True

class SemVer:
    """Handles semantic version parsing, comparison, and constraint matching."""

    _VERSION_RE = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:(?!0[0-9])[0-9A-Za-z-]+)(?:\.(?:(?!0[0-9])[0-9A-Za-z-]+))*))?"
        r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
    )

    @staticmethod
    def is_valid(version: object) -> bool:
        return isinstance(version, str) and SemVer._VERSION_RE.fullmatch(version.strip()) is not None

    @staticmethod
    def parse(version: str) -> Tuple[int, int, int, Tuple]:
        if not SemVer.is_valid(version):
            raise ValueError(f"Invalid semantic version: {version!r}")

        match = SemVer._VERSION_RE.fullmatch(version.strip())

        assert match is not None

        major, minor, patch, prerelease = match.groups()
        pre = tuple(
            int(identifier) if identifier.isdigit() else identifier
            for identifier in (prerelease.split(".") if prerelease else [])
        )

        return int(major), int(minor), int(patch), pre

    @staticmethod
    def compare(a: str, b: str) -> int:
        pa, pb = SemVer.parse(a), SemVer.parse(b)

        if pa[:3] != pb[:3]:
            return (pa[:3] > pb[:3]) - (pa[:3] < pb[:3])

        if pa[3] == pb[3]:
            return 0

        if not pa[3]:
            return 1

        if not pb[3]:
            return -1

        for left, right in zip(pa[3], pb[3]):
            if left == right:
                continue

            if isinstance(left, int) and isinstance(right, str):
                return -1

            if isinstance(left, str) and isinstance(right, int):
                return 1

            return (left > right) - (left < right)

        return (len(pa[3]) > len(pb[3])) - (len(pa[3]) < len(pb[3]))

    @staticmethod
    def satisfies(version: str, constraint: str) -> bool:
        if not SemVer.is_valid(version):
            return False

        if constraint in ("", "*", None):
            return True

        parts = [part.strip() for part in constraint.split(",") if part.strip()]

        for partConstraint in parts:
            if partConstraint.startswith("^"):
                try:
                    major, minor, patch, _ = SemVer.parse(partConstraint[1:])
                except ValueError:
                    return False

                lower = partConstraint[1:]
                upper = (
                    f"{major + 1}.0.0" if major > 0 else
                    f"0.{minor + 1}.0" if minor > 0 else
                    f"0.0.{patch + 1}"
                )

                if not (SemVer.satisfies(version, f">={lower}") and SemVer.satisfies(version, f"<{upper}")):
                    return False

            elif partConstraint.startswith("~"):
                try:
                    major, minor, patch, _ = SemVer.parse(partConstraint[1:])
                except ValueError:
                    return False

                lower, upper = partConstraint[1:], f"{major}.{minor+1}.0"

                if not (SemVer.satisfies(version, f">={lower}") and SemVer.satisfies(version, f"<{upper}")):
                    return False
            else:
                match = re.match(r"^(>=|<=|>|<|=)?\s*(.+)$", partConstraint)

                if not match:
                    return False
                
                operand, rhs = match.group(1) or "=", match.group(2)

                try:
                    comparison = SemVer.compare(version, rhs)
                except ValueError:
                    return False

                if operand == "=" and comparison != 0: return False
                if operand == ">" and comparison <= 0: return False
                if operand == "<" and comparison >= 0: return False
                if operand == ">=" and comparison < 0: return False
                if operand == "<=" and comparison > 0: return False
        
        return True

    @staticmethod
    def pick_best(available: List[str], constraint: Optional[str]) -> Optional[str]:
        sorted_versions = sorted(
            (version for version in available if SemVer.is_valid(version)),
            key=cmp_to_key(SemVer.compare),
            reverse=True,
        )

        for version in sorted_versions:
            if SemVer.satisfies(version, constraint):
                return version

        return None
