from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status


def _value(traveller: Any, field: str) -> str | None:
    value = traveller.get(field) if isinstance(traveller, dict) else getattr(traveller, field, None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _same_traveller(first: Any, second: Any) -> bool:
    first_name = _value(first, "full_name")
    second_name = _value(second, "full_name")
    if not first_name or not second_name or " ".join(first_name.split()).casefold() != " ".join(second_name.split()).casefold():
        return False

    first_mobile = _value(first, "mobile")
    second_mobile = _value(second, "mobile")
    if first_mobile and second_mobile and first_mobile.casefold() == second_mobile.casefold():
        return True

    first_email = _value(first, "email")
    second_email = _value(second, "email")
    return bool(
        first_email
        and second_email
        and first_email.casefold() == second_email.casefold()
    )


def ensure_unique_booking_travellers(
    travellers: Iterable[Any],
    existing: Iterable[Any] = (),
) -> None:
    seen = list(existing)
    for traveller in travellers:
        if any(_same_traveller(traveller, saved) for saved in seen):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This traveller already exists in the booking.",
            )
        seen.append(traveller)