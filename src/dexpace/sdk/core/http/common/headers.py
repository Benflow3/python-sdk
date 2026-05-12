"""Immutable, case-insensitive, multi-valued HTTP headers."""
from __future__ import annotations

from typing import Dict, Iterable, Iterator, Mapping, Optional, Tuple, Union

_HeaderValue = Union[str, Iterable[str]]
_Entries = Union[
    Mapping[str, _HeaderValue],
    Iterable[Tuple[str, _HeaderValue]],
]


class Headers:
    """Immutable, case-insensitive, multi-valued HTTP headers.

    Header names are normalised to lower case at storage time so lookup,
    membership, and equality are all case-insensitive. Insertion order of
    distinct names is preserved.

    Multi-value semantics: :meth:`with_added` appends to the values list for
    a name; :meth:`with_set` replaces the entire list. This matches the HTTP
    requirement that some headers (``Set-Cookie``, ``WWW-Authenticate``,
    ``Via``) may legitimately repeat.

    Instances are immutable and freely shareable across threads.
    """

    __slots__ = ("_data", "_hash")

    def __init__(self, entries: Optional[_Entries] = None) -> None:
        data: Dict[str, Tuple[str, ...]] = {}
        if entries is not None:
            items: Iterable[Tuple[str, _HeaderValue]]
            if isinstance(entries, Mapping):
                items = entries.items()
            else:
                items = entries
            for name, value in items:
                key = _normalize(name)
                existing = data.get(key, ())
                if isinstance(value, str):
                    data[key] = existing + (value,)
                else:
                    data[key] = existing + tuple(value)
        object.__setattr__(self, "_data", tuple(data.items()))
        object.__setattr__(self, "_hash", None)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Return the first value for ``name``, or ``default`` if absent."""
        target = _normalize(name)
        for key, values in self._data:
            if key == target:
                return values[0] if values else default
        return default

    def values(self, name: str) -> Tuple[str, ...]:
        """Return every value for ``name`` as a tuple; empty if absent."""
        target = _normalize(name)
        for key, values in self._data:
            if key == target:
                return values
        return ()

    def __getitem__(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value

    def __contains__(self, name: object) -> bool:
        if not isinstance(name, str):
            return False
        target = _normalize(name)
        return any(key == target for key, _ in self._data)

    def __iter__(self) -> Iterator[str]:
        for key, _ in self._data:
            yield key

    def __len__(self) -> int:
        return len(self._data)

    def names(self) -> Tuple[str, ...]:
        """Return the tuple of header names (lower-cased)."""
        return tuple(key for key, _ in self._data)

    def items(self) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
        """Return the underlying ``(name, values)`` tuples in insertion order."""
        return self._data

    def with_added(self, name: str, value: str) -> "Headers":
        """Return a new ``Headers`` with ``value`` appended to ``name``'s list."""
        target = _normalize(name)
        entries = []
        appended = False
        for key, values in self._data:
            if key == target:
                entries.append((key, values + (value,)))
                appended = True
            else:
                entries.append((key, values))
        if not appended:
            entries.append((target, (value,)))
        return _construct(tuple(entries))

    def with_set(self, name: str, *values: str) -> "Headers":
        """Return a new ``Headers`` with ``name`` set to exactly ``values``.

        If no values are provided, the header is removed.
        """
        if not values:
            return self.without(name)
        target = _normalize(name)
        entries = []
        replaced = False
        for key, existing in self._data:
            if key == target:
                if not replaced:
                    entries.append((key, tuple(values)))
                    replaced = True
                # else: drop any later duplicates
            else:
                entries.append((key, existing))
        if not replaced:
            entries.append((target, tuple(values)))
        return _construct(tuple(entries))

    def without(self, name: str) -> "Headers":
        """Return a new ``Headers`` with ``name`` removed (case-insensitive)."""
        target = _normalize(name)
        entries = tuple((key, values) for key, values in self._data if key != target)
        if len(entries) == len(self._data):
            return self
        return _construct(entries)

    def with_merged(self, other: "Headers") -> "Headers":
        """Append every entry from ``other`` to this headers."""
        merged: Dict[str, Tuple[str, ...]] = dict(self._data)
        for key, values in other._data:
            merged[key] = merged.get(key, ()) + values
        return _construct(tuple(merged.items()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Headers):
            return NotImplemented
        return self._data == other._data

    def __hash__(self) -> int:
        cached = self._hash
        if cached is None:
            cached = hash(self._data)
            object.__setattr__(self, "_hash", cached)
        return cached

    def __repr__(self) -> str:
        return f"Headers({{k: list(v) for k, v in self._data}})"  # show as dict-of-list

    @classmethod
    def empty(cls) -> "Headers":
        """Return the shared empty :class:`Headers` instance."""
        return _EMPTY


def _normalize(name: str) -> str:
    # HTTP header names are ASCII per RFC 7230, so casefold isn't needed and
    # lower-case is the canonical wire form for case-insensitive lookup.
    return name.lower().strip()


def _construct(data: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> Headers:
    instance = Headers.__new__(Headers)
    object.__setattr__(instance, "_data", data)
    object.__setattr__(instance, "_hash", None)
    return instance


_EMPTY = Headers()


__all__ = ["Headers"]
