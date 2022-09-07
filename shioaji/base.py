import typing
from enum import Enum
from pydantic import (
    BaseModel,
    conint,
    StrictInt,
    constr,
)
from pydantic.utils import ValueItems  # ,  sequence_like

# _missing = object()


class BaseModelV10(BaseModel):
    def __repr_args__(self):
        return [(k, v) for k, v in self._iter(to_dict=False, exclude_defaults=True)]

    def _iter(
        self,
        to_dict: bool = False,
        by_alias: bool = False,
        allowed_keys: typing.Optional["SetStr"] = None,
        include: typing.Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude: typing.Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        # exclude_none: bool = False,
    ):
        if not to_dict:
            if allowed_keys is None:
                allowed_keys = set(self.__fields__)
            if exclude:
                for k in exclude:
                    allowed_keys.discard(k)
        return super()._iter(
            to_dict,
            by_alias,
            allowed_keys,
            include,
            exclude,
            exclude_unset,
            exclude_defaults,
            # exclude_none,
        )

    @classmethod
    def _get_value(
        cls,
        v: typing.Any,
        to_dict: bool,
        by_alias: bool,
        include: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude_unset: bool,
        exclude_defaults: bool,
        # exclude_none: bool,
    ) -> typing.Any:
        if to_dict and isinstance(v, Enum):
            return v.value
        return super()._get_value(
            v,
            to_dict,
            by_alias,
            include,
            exclude,
            exclude_unset,
            exclude_defaults,
            # exclude_none,
        )

    def keys(self) -> typing.List[typing.Any]:
        return self._calculate_keys(include=None, exclude=None, exclude_unset=True)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        return self._get_value(
            self.__dict__[key],
            to_dict=True,
            by_alias=False,
            include=None,
            exclude=None,
            exclude_unset=True,
            exclude_defaults=True,
            # exclude_none=True,
        )


class BaseModelV15(BaseModel):
    def __repr_args__(self):
        return [(k, v) for k, v in self._iter(to_dict=False, exclude_defaults=True)]

    @classmethod
    def _get_value(
        cls,
        v: typing.Any,
        to_dict: bool,
        by_alias: bool,
        include: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
    ) -> typing.Any:
        if to_dict and isinstance(v, Enum):
            return v.value
        return super()._get_value(
            v,
            to_dict,
            by_alias,
            include,
            exclude,
            exclude_unset,
            exclude_defaults,
            exclude_none,
        )

    def keys(self) -> typing.List[typing.Any]:
        return self._calculate_keys(include=None, exclude=None, exclude_unset=True)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        return self._get_value(
            self.__dict__[key],
            to_dict=True,
            by_alias=False,
            include=None,
            exclude=None,
            exclude_unset=True,
            exclude_defaults=True,
            exclude_none=True,
        )


class MetaProps(type):
    def __repr__(cls):
        attrs = [attr for attr in cls.__dict__ if not attr.startswith("_")]
        display_name = cls.__name__ if not cls.__name__.startswith("_") else ""
        return "{}({})".format(display_name, (", ").join(attrs))


class BaseProps(metaclass=MetaProps):
    pass


from importlib_metadata import version

if version("pydantic") > "1.0":
    BaseModel = BaseModelV15
else:
    BaseModel = BaseModelV10
