_record_cache = {}


class _Record:
    """Base class to represent a project resource being tracked

    records are unique per name but may contain mutable search information
    """

    @staticmethod
    def _normalize_name(name):
        return name

    def __new__(cls, *args, **kwargs):
        name = cls._normalize_name(kwargs.get('name', args[0]))
        if (cls, name) in _record_cache:
            record = _record_cache[(cls, name)]
        else:
            record = super().__new__(cls)
            _record_cache[(cls, name)] = record
        return record

    def __init__(self, name):
        self._normalized_name = self._normalize_name(name)

    def __hash__(self):
        return hash(self.name)

    @property
    def name(self):
        return self._normalized_name
