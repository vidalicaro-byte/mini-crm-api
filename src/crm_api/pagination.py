from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def _pagination(
    page: Annotated[int, Query(ge=1, description="Page number, starting at 1.")] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(_pagination)]


def _full_list(max_size: int) -> Any:
    """Pagination for lists the front end loads whole (the board's deals, a contact's activities):
    without parameters, one page holds everything up to `max_size`."""

    def dependency(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(alias="pageSize", ge=1, le=max_size)] = max_size,
    ) -> Pagination:
        return Pagination(page=page, page_size=page_size)

    return dependency


DealsPaginationDep = Annotated[Pagination, Depends(_full_list(200))]
ActivitiesPaginationDep = Annotated[Pagination, Depends(_full_list(100))]
