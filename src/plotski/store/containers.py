"""Container classes."""
import math
import typing as ty
from abc import abstractmethod

T = ty.TypeVar("T")


class Container(ty.MutableSequence):
    """Container for figures contained in the PlotStore using `grid` layout."""

    def __init__(self, data: ty.Iterable = ()):
        self._data = []
        self._data.extend(data)

    @ty.overload
    @abstractmethod
    def __getitem__(self, i: int) -> T:
        ...

    @ty.overload
    @abstractmethod
    def __getitem__(self, s: slice) -> ty.MutableSequence[T]:  # noqa: F811
        ...

    def __getitem__(self, i: int) -> T:  # noqa: F811
        return self._data[i]

    @ty.overload
    @abstractmethod
    def __setitem__(self, i: int, o: T) -> None:
        ...

    @ty.overload
    @abstractmethod
    def __setitem__(self, s: slice, o: ty.Iterable[T]) -> None:  # noqa: F811
        ...

    def __setitem__(self, i: int, o: T) -> None:  # noqa: F811
        self._data[i] = o

    @ty.overload
    @abstractmethod
    def __delitem__(self, i: int) -> None:
        ...

    @ty.overload
    @abstractmethod
    def __delitem__(self, i: slice) -> None:  # noqa: F811
        ...

    def __delitem__(self, i: int) -> None:  # noqa: F811
        del self._data[i]

    def __len__(self) -> int:
        return len(self._data)

    def insert(self, index: int, value: T) -> None:
        """Insert data."""
        self._data.insert(index, value)


class Individual(Container):
    """Container for figures contained in the PlotStore without layout."""


class Row(Container):
    """Container for figures contained in the PlotStore using `row` layout."""


class Column(Container):
    """Container for figures contained in the PlotStore using `column` layout."""


class Grid(Container):
    """Container for figures contained in the PlotStore using `grid` layout."""

    _n_cols: ty.Optional[int] = None

    @property
    def n_cols(self):
        """Number of columns used to represent the grid layout."""
        if self._n_cols is None:
            return math.ceil(math.sqrt(len(self)))
        return self._n_cols

    @n_cols.setter
    def n_cols(self, value: int):
        self._n_cols = value
