from inspect import getmembers, isclass
import re

from app.core.enums import ALLOWED_ENUM_GROUPS, AppEnum
from app.schemas.enum import EnumGroup, EnumListResponse, EnumOption


class EnumService:
    @staticmethod
    def _display_label(value: str) -> str:
        spaced_value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
        return spaced_value.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _enum_groups() -> list[type[AppEnum]]:
        from app.core import enums

        return [
            enum_class
            for _, enum_class in getmembers(enums, isclass)
            if (
                issubclass(enum_class, AppEnum)
                and enum_class is not AppEnum
                and enum_class.__name__ in ALLOWED_ENUM_GROUPS
            )
        ]

    @staticmethod
    def allowed_group_names() -> tuple[str, ...]:
        return ALLOWED_ENUM_GROUPS

    def list_enums(
        self,
        group: str | None = None,
        search: str | None = None,
    ) -> EnumListResponse:
        search_text = search.strip().casefold() if search else None
        requested_group = group.strip().casefold() if group else None
        enum_groups: list[EnumGroup] = []
        flat_options: list[dict[str, str]] = []

        for enum_class in self._enum_groups():
            enum_name = enum_class.__name__
            if requested_group and enum_name.casefold() != requested_group:
                continue

            options = [
                EnumOption(
                    value=member.value,
                    label=self._display_label(member.value),
                )
                for member in enum_class
                if not search_text
                or search_text in enum_name.casefold()
                or search_text in member.name.casefold()
                or search_text in str(member.value).casefold()
                or search_text in self._display_label(str(member.value)).casefold()
            ]
            if not options:
                continue

            enum_groups.append(
                EnumGroup(
                    name=enum_name,
                    label=self._display_label(enum_name),
                    options=options,
                )
            )
            flat_options.extend(
                {
                    "group": enum_name,
                    "value": option.value,
                    "label": option.label,
                }
                for option in options
            )

        return EnumListResponse(groups=enum_groups, options=flat_options)
