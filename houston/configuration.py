__all__ = ['Option', 'Configuration', 'option']

from typing import Type, FrozenSet, Dict, Any
import attr
import logging

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True)
class Option(object):
    """
    Describes a configuration option in terms of its type and legal
    values.
    """
    name = attr.ib(type=str)
    typ = attr.ib(type=Type)

    @property
    def _field(self) -> str:
        return "__{}".format(self.name)

    @attr.s(frozen=True)
    class Builder(object):
        typ = attr.ib(type=Type)

        def build(self, name: str) -> 'Option':
            return Option(name, self.typ)


def option(*args, **kwargs) -> Option.Builder:
    return Option.Builder(*args, **kwargs)


class ConfigurationMeta(type):
    def __new__(mcl,
                cls_name: str,
                bases,  # FIXME
                ns: Dict[str, Any]
                ):
        # collect and build option definitions
        builders = {}  # type: Dict[str, Option.Builder]
        for name in ns:
            if isinstance(ns[name], Option.Builder):
                logger.debug("found option: %s", name)
                builders[name] = ns[name]
        logger.debug("building options")
        options = frozenset(
            b.build(name) for (name, b) in builders.items()
        )  # type: FrozenSet[Option]
        logger.debug("built options: %s", options)

        logger.debug("storing options in options property")
        ns['options'] = options
        logger.debug("stored options in options property")

        logger.debug("constructing options")
        for option in options:
            getter = lambda self, f=option._field: getattr(self, f)
            ns[option.name] = property(getter)
        logger.debug("constructed options")

        return super().__new__(mcl, cls_name, bases, ns)


class Configuration(object, metaclass=ConfigurationMeta):
    @classmethod
    def from_dict(cls: Type['Configuration'],
                  dkt: Dict[str, Any]
                  ) -> 'Configuration':
        return cls(**dkt)

    def __init__(self, *args, **kwargs) -> None:
        cls_name = self.__class__.__name__
        options = self.__class__.options  # type: FrozenSet[Option]

        # were any positional arguments passed to the constructor?
        if args:
            msg = "constructor [{}] accepts no positional arguments but {} {} given"  # noqa: pycodestyle
            msg = msg.format(cls_name,
                             "was" if len(args) == 1 else "were",
                             len(args))
            raise TypeError(msg)

        # set values for each option
        for opt in options:
            try:
                val = kwargs[opt.name]
            except KeyError:
                msg = "missing keyword argument [{}] to constructor [{}]"
                msg = msg.format(opt.name, cls_name)
                raise TypeError(msg)
            setattr(self, opt._field, val)

        # were any unexpected keyword arguments provided?
        if len(kwargs) > len(options):
            actual_args = set(n for n in kwargs)
            expected_args = set(opt.name for opt in options)
            unexpected_arguments = list(actual_args - expected_args)
            msg = "unexpected keyword arguments [{}] supplied to constructor [{}]"  # noqa: pycodestyle
            msg = msg.format('; '.join(unexpected_arguments), cls_name)
            raise TypeError(msg)

    def __getitem__(self, name: str) -> Any:
        # FIXME use frozendict
        try:
            options = self.__class__.options
            opt = next(opt for opt in options if opt.name == name)
        except StopIteration:
            msg = "no option [{}] in state [{}]"
            msg.format(name, self.__class__.__name__)
            raise KeyError(msg)
        return getattr(self, opt._field)

    def __hash__(self) -> int:
        all_opts = [self[opt.name] for opt in self.__class__.options]
        all_opts.insert(0, self.__class__.__name__)
        return hash(tuple(all_opts))

    def __eq__(self, other: 'Configuration') -> bool:
        if type(self) != type(other):
            msg = "illegal comparison of configurations: [{}] vs. [{}]"
            msg = msg.format(self.__class__.__name__, other.__class__.__name__)
            raise Exception(msg)  # FIXME use HoustonException
        return self.__dict__ == other.__dict__

    def to_dict(self) -> Dict[str, Any]:
        fields = {}  # type: Dict[str, Any]
        for opt in self.__class__.options:
            fields[opt.name] = getattr(self, opt._field)
        return fields

    def __repr__(self) -> str:
        fields = self.to_json()
        for (name, val) in fields.items():
            if isinstance(val, float):
                s = "{:.3f}".format(val)
            else:
                s = str(val)
            fields[name] = val
        s = '; '.join(["{}: {}".format(k, v) for (k, v) in fields.items()])
        s = "{}({})".format(self.__class__.__name__, s)
        return s
