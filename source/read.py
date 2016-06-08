"""Import old style data"""
import os
import subprocess

from tables import tables_init
from server import Server
from fields import Set, Relation, Store


class Unresolved(object):
    """Element of a list of unresolved relations during the reading"""
    def __init__(self, obj, fldName, data, line_nr):
        self.obj = obj  # the object where the relation should be written
        self.fldName = fldName  # the name of the field to write
        self.data = data  # the hash to resolve the object with
        self.line_nr = line_nr  # the line where the relation was encountered


class Scanner(object):
    """Define the global fields of the file scanner"""
    def __init__(self, fp):
        self.fp = fp
        self.line = ''
        self.line_nr = 0
        self.pos = 0
        self.stop = not self._next_line()
        self.unresolved = []

    def _next(self):
        """Return the next character found or '' on end of line"""
        if self.stop or self.pos == len(self.line):
            return ''
        return self.line[self.pos]

    def _has_next(self, *char):
        """Return True is the given char is found and skip it"""
        if self._next() in char:
            self.pos += 1
            return True
        return False

    def _expect(self, char, excep):
        """The next character chould be char or raise and exception"""
        if self.stop or self.pos == len(self.line) or \
                self.line[self.pos] != char:
            raise ValueError(excep)
        self.pos += 1

    def _next_line(self):
        """Read the next line from the file"""
        try:
            self.line = self.fp.__next__()
            if self.line.endswith('\n'):
                self.line = self.line[:-1]
            self.pos = 0
            self.line_nr += 1
            return True
        except StopIteration:
            self.line = ''
            self.pos = 0
            self.stop = True
            return False

    def _skip_whitespace(self):
        """Skip whitespace and comments"""
        while self._has_next('\n', '\t', ' ', '\b'):
            pass
        if self._next() == '#':  # comment found
            self.pos = len(self.line)

    def _scan_indent(self, indent):
        """Check for the correct indentation"""
        self.pos = 0
        for _ in range(indent * 2):
            if self._next() == '#':
                self.pos = len(self.line)
                return
            self._expect(' ', "Expect correct indentation")
        if self._next() == '#':
            self.pos = len(self.line)

    def _scan_field(self):
        """Read a field from the file"""
        self._skip_whitespace()
        field = ''
        while 'a' <= self._next() <= 'z' or self._next() == '_':
            field += self._next()
            self.pos += 1
        if len(field) == 0:
            raise ValueError("Expected a field")
        return field

    def _scan_value(self, relation=False):
        """Read a value from the file"""
        value = ''
        test = [',', '}'] if relation else [',']
        while self._next() not in test:
            if self.pos < len(self.line) - 1 and \
                    self.line[self.pos] == '\\' and \
                    self.line[self.pos + 1] in [',', '}']:
                value += self.line[self.pos + 1]
                self.pos += 2
            elif self.pos < len(self.line):
                value += self.line[self.pos]
                self.pos += 1
            else:
                break
        return value

    def _scan_multi_line(self, rec, fld, indent):
        """Scan a multi-line string"""
        self._next_line()
        res = ""
        while self.line.startswith('  ' * indent):
            if res:
                res += "\n"
            res += self.line[indent * 2:]
            self._next_line()
        setattr(rec, fld.name, res)

    def _scan_set(self, rec, fld, indent):
        """Scan a set of sub records"""
        self._skip_whitespace()
        self._expect('[', "Expect '[' at the start of a Set")
        if self._has_next(']'):  # empty set
            return
        if self.pos < len(self.line):
            raise ValueError("Expect '[' at the end of a line")
        if not self._next_line():
            raise ValueError("Expect ']' after a set")
        while not self.stop:
            if self.line.startswith('  ' * (indent - 1) + "]"):
                break
            sub = fld.related(rec)
            if self._read_record(sub, indent):
                sub.store()
        if self.stop:
            raise ValueError("Expect ']' after a set")
        self.pos = 2 * indent - 1

    def _scan_relation(self, rec, fld):
        """Scan a relation to another record"""
        data = {}
        self._skip_whitespace()
        self._expect('{', "Expect '{' at the start of Relation")
        if self._next() != '}':
            while True:
                field = self._scan_field()
                self._skip_whitespace()
                self._expect('=', "Expect a '=' after a field")
                data[field] = self._scan_value(True)
                if self._has_next(','):
                    continue
                self._expect('}', "Expect a '}' after relation data")
                break
            found = fld.find(data)
            if found is None:
                self.unresolved.append(
                    Unresolved(rec, fld.name, data, self.line_nr))
            else:
                setattr(rec, fld.name, fld.find(data))

    def _read_record(self, rec, indent):
        """Create a record from the new style file"""
        self._scan_indent(indent)
        while self.pos == len(self.line):
            if not self._next_line() or \
                    self.line.startswith('  ' * (indent - 1) + "]"):
                return False
            self._scan_indent(indent)
        while self.pos < len(self.line):
            field = self._scan_field()
            self._skip_whitespace()
            self._expect('=', "Expect a '=' after a field")
            fld = rec.field(field)
            if isinstance(fld, Set):
                self._scan_set(rec, fld, indent + 1)
            elif isinstance(fld, Relation):
                self._scan_relation(rec, fld)
            elif self.pos == len(self.line):
                self._scan_multi_line(rec, fld, indent + 1)
                if self.line.startswith('  ' * indent + "& "):
                    self.pos = indent * 2 + 2
                else:
                    break
            else:
                value = self._scan_value()
                setattr(rec, field, fld.read(value))
            self._has_next(',')
            self._skip_whitespace()
            if self.pos == len(self.line):  # check for continuation
                if self._next_line() and \
                        self.line.startswith('  ' * indent + "& "):
                    self.pos = indent * 2 + 2
                else:
                    break
        return True

    def read(self, general):
        """Read data from a file"""
        try:
            self._read_record(general, 0)
        except ValueError as exc:
            raise ValueError(str(exc) + " on line " + str(self.line_nr))

    def resolve(self):
        """Try to resolve the previous unresolved relations"""
        for rel in self.unresolved:
            fld = rel.obj.field(rel.fldName)
            found = fld.find(rel.obj, rel.data)
            if found is None:
                raise ValueError(
                    "Unresolved relation " + fld.related.__name__ + " " +
                    str(rel.data) + " on line " + str(self.line_nr))
            setattr(rel.obj, rel.fldName, found)


def do_scan(fp, general):
    """Scan a set of lines"""
    scan = Scanner(fp)
    scan.read(general)
    scan.resolve()


def scan_file(filename, general):
    """Read the new style data file"""
    fp = open(filename)
    do_scan(fp, general)
    fp.close()


def reading(string):
    """Read data from a string instead of a file after clearing everything"""
    store = Store()
    general = tables_init(store)
    do_scan(string.split('\n').__iter__(), general)
    return general


def main():
    """Start a server"""
    file = '../data/game.dbr'
    store = Store()
    game = tables_init(store)
    scan_file(file, game)
    game.output('../data/game.new')
    if os.system('/usr/bin/cmp -s ../data/game.dbr ../data/game.new'):
        subprocess.Popen([
            '/usr/bin/meld', '../data/game.dbr', '../data/game.new'])
    else:
        os.unlink('../data/game.new')
        html_path = "../html"
        serv = Server(game, html_path, file)
        serv.start()


if __name__ == "__main__":
    main()
