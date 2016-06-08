"""Possible types for fields"""
import re
from abc import ABCMeta, abstractmethod
from datetime import date, datetime

# pylint: disable=no-self-use

LINE_LENGTH = 120


class Store(object):
    """Central object holding a data store"""
    def __init__(self):
        self.root = None
        self._changes = False

    def changes(self, remember_changes=True):
        """Start or stop remembering changes on records"""
        self._changes = remember_changes
        for fld in self.root.fields:
            if not isinstance(fld, Set) or not fld.primary:
                continue
            getattr(self.root, fld.name).remember_changes(self._changes)

    def init(self, root):
        """Set the root product of the store"""
        self.root = root

    def register(self, *classes):
        """Register a set of classes to the store"""
        names = {}
        for fld in self.root.fields:
            names[fld.name] = fld
        setattr(self.root.__class__, 'field_on_name', names)
        setattr(self.root.__class__, 'data_store', self)
        for clazz in classes:
            names = {}
            for fld in clazz.fields:
                names[fld.name] = fld
            setattr(clazz, 'field_on_name', names)
            setattr(clazz, 'data_store', self)


class Number:
    """Number type"""
    def __init__(self, name, allow_null=False):
        self.name = name
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        try:
            data = str(data)
            if data.startswith("0b"):
                return int(data[2:], 2)
            if data.startswith("0o"):
                return int(data[2:], 8)
            if data.startswith("0x"):
                return int(data[2:], 16)
            return int(data)
        except ValueError:
            raise ValueError("Invalid Number value '" + data + "'")

    def write(self, data):
        """Write data to a file"""
        return str(data)

    def show(self, data):
        """Show the data inside an html file"""
        if data is None:
            return ""
        return str(data)


class Amount:
    """Amount type"""
    def __init__(self, name, allow_null=False):
        self.name = name
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        act = data
        if isinstance(data, float):
            return int(data * 100)
        elif isinstance(data, int):
            return data
        pos = data.find('.')
        if pos >= 0:
            data += '0' * (3 - len(data) + pos)
            data = data.replace('.', '', 1)
        try:
            return int(data)
        except ValueError:
            raise ValueError("Invalid Amount value '" + str(act) + "'")

    def write(self, data):
        """Write data to a file"""
        if data is None:
            return "0.00"
        return "{:.2f}".format(data / 100)

    def show(self, data):
        """Show the data inside an html file"""
        if data is None:
            return "0.00"
        return "{:.2f}".format(data / 100)


class Enum:
    """Enum type with a set of values"""
    def __init__(self, name, values, allow_null=False):
        self.name = name
        self.values = values
        self.allow_null = allow_null
        self.onName = {}
        i = 1
        for v in values:
            self.onName[v] = i
            i += 1

    def read(self, data):
        """Read data from a file"""
        if data in self.onName:
            return self.onName[data]
        if re.match(r"\d+", data):
            return int(data) + 1
        raise ValueError("Invalid Enum value '" + data + "'")

    def write(self, data):
        """Write data to a file"""
        return self.values[data - 1]

    def show(self, data):
        """Show the data inside an html file"""
        return self.values[data - 1]


class Date:
    """Date field"""
    date_format = '%Y-%m-%d'

    def __init__(self, name, allow_null=False):
        self.name = name
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        try:
            return datetime.strptime(data, Date.date_format)
        except ValueError:
            raise ValueError("Invalid Date value '" + data + "'")

    def write(self, data):
        """Write data to a file"""
        return date.strftime(data, Date.date_format)

    def show(self, data):
        """Show the data inside an html file"""
        if data is None:
            return ""
        return date.strftime(data, Date.date_format)


class String:
    """String field"""
    def __init__(self, name, allow_null=False):
        self.name = name
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        return str(data)

    def write(self, data):
        """Write data to a file"""
        return data

    def show(self, data):
        """Show the data inside an html file"""
        if data is None:
            return ""
        return data


class Boolean:
    """Boolean field"""
    def __init__(self, name, allow_null=False):
        self.name = name
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        return bool(data == "true" or data == 1)

    def write(self, data):
        """Write data to a file"""
        return "true" if data else "false"

    def show(self, data):
        """Show the data inside an html file"""
        return "true" if data else "false"


class Relation:
    """Relation to another record"""
    def __init__(self, name, related, allow_null=False):
        self.name = name
        self.related = related
        self.allow_null = allow_null

    def read(self, data):
        """Read data from a file"""
        find = None
        for key in self.related.keys:
            fld = self.related.field_on_name[key]
            find = fld.read(data)
        root = self.related.data_store.root
        if self.related.path:
            return getattr(root, self.related.path)[find]
        return root

    def write(self, data):
        """Write data to a file"""
        if data is None:
            return "{}"
        return data.key_repr()

    def show(self, data):
        """Show the data inside an html file"""
        if data is None:
            return "???"
        return data.show()

    def find(self, data):
        """Find a related record"""
        return self.related.find(self.related, data=data)


class Set:
    """Set of records"""
    def __init__(self, name, related, primary=True):
        self.name = name
        self.related = related
        self.primary = primary
        self.allow_null = True


class Record(metaclass=ABCMeta):
    """Record"""
    def root(self):
        """Get the root object of the data store"""
        return getattr(self, 'data_store').root

    @abstractmethod
    def store(self):
        """Abstract method to store a record"""
        pass

    @abstractmethod
    def remove(self):
        """Abstract method to remove a record from indexes"""
        pass

    @abstractmethod
    def removable(self, general):
        """Routine to check if a record may safely be removed"""
        return None

    def get_name(self):
        """Return the name of the current record"""
        return self.__class__.__name__.lower()

    def field(self, name):
        """Return the definition of a field"""
        names = getattr(self, 'field_on_name')
        if name not in names:
            raise KeyError(name + " not found in " + self.__class__.__name__)
        return names[name]

    def imp(self, data, change=False):
        """Read a dict of values into this record"""
        if change:
            self.remove()
        names = getattr(self, 'field_on_name')
        for key, value in data.items():
            if key in names:
                setattr(self, key, names[key].read(value))
            else:
                raise ValueError("Unknown field '" + key + "'")
        self.store()

    def validate(self, data, add=False):
        """Validate the given field data"""
        res = {}
        keys = set(getattr(self, 'keys'))
        names = getattr(self, 'field_on_name')
        open_flds = set(names.keys())
        for key, value in data.items():
            if key in names:
                if value is None and (
                        key in keys or not names[key].allow_null):
                    res[key] = 'Cannot be empty'
                    continue
                try:
                    names[key].read(value)
                except ValueError as e:
                    res[key] = e.args[0]
                except KeyError as e:
                    res[key] = 'Unknown key "' + e.args[0] + '"'
                open_flds.remove(key)
            else:
                res[key] = "Unknown field"
        if add:
            for key in open_flds:
                if key in keys:
                    res[key] = 'Missing field'
                    continue
                fld = names[key]
                if not fld.allow_null:
                    res[key] = 'Cannot be empty'
        return res

    def get_key(self):
        """Create a presentation of the keys of this record"""
        ls = []
        for key in getattr(self, 'keys'):
            fld = self.field(key)
            if isinstance(fld, Number) or isinstance(fld, Enum):
                ls.append("{:07d}".format(getattr(self, key)))
            else:
                ls.append(str(fld.write(getattr(self, key))))
        return '|'.join(ls)

    def get_id(self):
        """Create a presentation of the id of this record"""
        id_fld = getattr(self, 'id_fld', None)
        if not id_fld:
            return self.get_key()
        val = getattr(self, id_fld)
        if isinstance(val, int):
            return "{:07d}".format(val)
        return self.field(id_fld).write(val)

    def key_repr(self):
        """Create a presentation of the key of this record"""
        ls = ['{']
        for key in getattr(self, 'keys'):
            if len(ls) > 1:
                ls.append(', ')
            ls.append(key)
            ls.append('=')
            fld = self.field(key)
            ls.append(fld.write(getattr(self, fld.name)).replace(",", "\\,"))
        ls.append('}')
        return ''.join(ls)

    def __repr__(self):
        out = Output()
        out.to_str(self, 0)
        return ''.join(out.ls)

    def changes(self):
        """Show only changes to the structure"""
        out = Output()
        store = getattr(self, 'data_store')
        changed = getattr(store, 'changed', self)
        out.changes(changed, self, 0)
        return ''.join(out.ls)

    def output(self, file):
        """Write the new format record data to a file"""
        fp = open(file, "w")
        out = Output()
        out.to_str(self, 0)
        for val in out.ls:
            fp.write(val)
        fp.close()


class Output(object):
    """Make string presentation"""
    def __init__(self):
        self.pos = 0
        self.ls = []
        self.start = True  # before first field on a line

    def _write(self, val, indent):
        """Try to fit a value on the current line"""
        comma = 0 if self.start else 2
        if self.pos == -1 or self.pos + len(val) + comma > LINE_LENGTH:
            self.ls.append("\n")
            self.ls.append('  ' * indent)
            self.ls.append('& ')
            self.pos = 2 * indent + 2
            self.start = False
        elif self.start:
            self.start = False
        else:
            self.ls.append(', ')
            self.pos += 2
        self.ls.append(val)
        self.pos += len(val)

    def _write_set(self, rec, fld, indent):
        """Write a set"""
        if not fld.primary:
            return
        recs = getattr(rec, fld.name)
        if len(recs) == 0:
            self._write(fld.name + '=[]', indent)
            return
        self._write(fld.name + '=[\n', indent)
        for record in recs:
            self.to_str(record, indent + 1)
            self.ls.append('\n')
            self.pos = 0
        self.ls.append('  ' * indent)
        self.ls.append(']')
        self.pos = indent * 2 + 1

    def _write_val(self, rec, fld, indent):
        """Write a value, possibly a multi line string"""
        val = getattr(rec, fld.name)
        if val and isinstance(fld, String):
            show = val.split('\n')
            if len(show) > 1 or len(show[0]) > 80:
                self._write(fld.name + "=", indent)
                for val in show:
                    self.ls.append("\n")
                    self.ls.append('  ' * (indent + 1))
                    self.ls.append(val)
                self.pos = -1
            else:
                val = show[0].replace(",", "\\,")
                self._write(fld.name + "=" + val, indent)
        elif val:
            show = fld.write(val)
            self._write(fld.name + "=" + show, indent)

    def to_str(self, rec, indent):
        """Create a list with the formatted data of the record"""
        self.start = True
        self.ls.append('  ' * indent)
        self.pos = indent * 2
        for fld in getattr(rec, 'fields'):
            if isinstance(fld, Set):
                self._write_set(rec, fld, indent)
            elif hasattr(rec, fld.name):
                self._write_val(rec, fld, indent)

    def _changed_set(self, rec, fld, indent):
        """Show changes in sets"""
        if not fld.primary:
            return
        recs = getattr(rec, fld.name)
        if not recs.has_changes():
            return
        self._write(fld.name + '=[\n', indent)
        for old, cur in recs.changes():
            self.changes(old, cur, indent + 1)
            self.ls.append('\n')
            self.pos = 0
        self.ls.append('  ' * indent)
        self.ls.append(']')
        self.pos = indent * 2 + 1

    def changes(self, old, cur, indent):
        """Show minimalized changes between two objects"""
        if old is None:  # new record.. show all
            self.to_str(cur, indent)
            return
        if cur is None:  # deleted record.. show key
            self.start = True
            self.ls.append('  ' * indent)
            self.ls.append("! ")
            for fldkey in old.keys:
                self._write_val(old, old.field_on_name[fldkey], indent)
            return
        self.start = True
        self.ls.append('  ' * indent)
        self.pos = indent * 2
        for fld in old.fields:
            fnm = fld.name
            if isinstance(fld, Set):
                self._changed_set(cur, fld, indent)
                continue
            oval = getattr(old, fnm, None)
            nval = getattr(cur, fnm, None)
            if fld.name not in old.keys and (
                    (oval is None and nval is None) or oval == nval):
                continue
            if getattr(cur, fnm, None) is None:
                self.ls.append(fnm)
                self.ls.append("!")
            else:
                self._write_val(cur, fld, indent)
