"""A server that allows a web application to get information about records
   and change them"""
import asyncio
import json
import re
from collections import OrderedDict

from websockets.server import serve
from fields import Set, Enum, Relation
import export
import form

REGEX = re.compile(r",\n *\"", re.MULTILINE)
REGEX2 = re.compile(r"{\n *", re.MULTILINE)
REGEX3 = re.compile(r"\n *}", re.MULTILINE)


def layout(obj):
    """JSON version of the data strucutre"""
    res = json.dumps(obj, indent=2, separators=(',', ':'), sort_keys=True)
    res = REGEX.sub(", \"", res)
    res = REGEX2.sub("{", res)
    res = REGEX3.sub("}", res)
    return res


def show_documentation():
    """Show a simple documentation page"""
    doc = [
        {
            "command": "/fields/",
            "use": "Get information about fields defined in the data set."
        },
        {"command": '/record/', "use": "Get data from records."},
        {"command": '/write/', "use": "Write data to records."},
        {"command": '/list/', "use": "HTML list of records."},
        {"command": '/form/', "use": "HTML form for a record."},
    ]
    return doc


def field_values(fld, general):
    """Get a dictionary with information and possible values of a field"""
    info = OrderedDict()
    info['name'] = fld.name
    info['type'] = type(fld).__name__
    if isinstance(fld, Enum):
        info['values'] = fld.values
    if isinstance(fld, Relation):
        ls = []
        if fld.allow_null:
            ls.append({'key': '', 'value': ''})
        for rec in getattr(general, fld.related.path):
            ls.append({'key': rec.get_id(), 'value': rec.show()})
        info['values'] = ls
    return info


def _change_record(clazz, rec, data, recset, key):
    """Change a record in the data set"""
    show = OrderedDict()
    res = clazz.validate(clazz, data)  # validate data before changing
    if res:
        show['action'] = 'error'
        show['message'] = 'Errors in fields'
        show['fields'] = res
        return show
    try:
        rec.imp(data, change=True)
    except ValueError as e:
        if e.args[0] == 'Remove an item before storing a changed one':
            recset.restore(key)
            res = {}
            for fld_key in clazz.keys:
                fld = clazz.field_on_name[fld_key]
                res[fld.name] = 'Duplicate key'
            show['action'] = 'error'
            show['message'] = 'Errors in fields'
            show['fields'] = res
            return show
        else:
            raise e
    show['action'] = 'updated'
    return show


class Server(object):
    """Server that handles requests for data on records and record changes"""
    def __init__(self, general, path, file):
        self.loop = None
        self.server = None
        self.general = general
        self.path = path
        self.file = file
        self.records = OrderedDict()
        gen_class = general.__class__
        self.records[gen_class.__name__.lower()] = gen_class
        for fld in self.general.fields:
            if isinstance(fld, Set):
                self.records[fld.related.__name__.lower()] = fld.related

    def show_table(self):
        """Show a list of known tables"""
        tables = []
        for tbl in self.records:
            tables.append(tbl)
        return tables

    def record_info(self, record):
        """Show the content of a record"""
        pos = record.find("/")
        if pos <= 0 or pos == len(record) - 1:
            ls = []
            if pos > 0:
                record = record[:pos]
            for rec in getattr(self.general, self.records[record].path):
                ls.append({'key': rec.get_id(), 'show': rec.show()})
            return ls
        show = OrderedDict()
        try:
            table = record[:pos]
            records = getattr(self.general, self.records[table].path)
            rec = records[record[pos + 1:]]
            show['title'] = type(rec).__name__ + " " + rec.show()
            show['record'] = table
            show['key'] = rec.get_id()
            fields = []
            for fld in rec.fields:
                if isinstance(fld, Set):
                    continue
                info = field_values(fld, self.general)
                val = getattr(rec, fld.name)
                if isinstance(fld, Relation) and val:
                    info['value'] = val.get_id()
                elif val:
                    info['value'] = fld.write(val)
                else:
                    info['value'] = None
                fields.append(info)
            show['fields'] = fields
        except KeyError:
            show['action'] = 'error'
            key = record[pos + 1:]
            show['message'] = 'Unknown ' + record[:pos] + ' "' + key + '"'
            ls = []
            for rec in getattr(self.general, self.records[record[:pos]].path):
                ls.append(rec.get_id())
            show['keys'] = ls
        return show

    def record_delete(self, record):
        """Remove a record from the store"""
        pos = record.find("/")
        show = OrderedDict()
        if pos <= 0 or pos == len(record) - 1:
            show['action'] = 'error'
            show['message'] = "Give a key to a current record to delete"
            return show
        table = record[:pos]
        key = record[pos + 1:]
        records = getattr(self.general, self.records[table].path)
        if key not in records:
            return {
                'action': 'error',
                'message': 'Unknown ' + table + ' "' + key + '"'}
        rec = records[key]
        problem = rec.removable(self.general)
        if problem is not None:
            show['action'] = 'error'
            for k, v in problem.items():
                show[k] = v
        else:
            rec.remove()
            show['action'] = 'deleted'
        return show

    def list_records(self, record, data):
        """Show html table of records"""
        return export.serve(
            self.general, record, json.loads(data) if data else {})

    def _add_record(self, record, data):
        """Add a record to the data set"""
        rec = self.records[record]
        res = rec.validate(rec, data, add=True)  # validate data
        show = OrderedDict()
        if res:
            show['action'] = 'error'
            show['message'] = 'Errors in fields'
            show['fields'] = res
            return show
        rec = self.records[record](self.general)
        try:
            rec.imp(data)
        except ValueError as e:
            if e.args[0] == 'Remove an item before storing a changed one':
                res = {}
                for fld_key in rec.keys:
                    fld = rec.field_on_name[fld_key]
                    res[fld.name] = 'Duplicate key'
                show['action'] = 'error'
                show['message'] = 'Errors in fields'
                show['fields'] = res
                return show
            else:
                raise e
        show['action'] = 'added'
        return show

    def record_write(self, record, data):
        """Change the content of a record"""
        show = OrderedDict()
        if data:
            data = json.loads(data)
        pos = record.find("/")
        if pos == len(record) - 1:
            record = record[:pos]
            pos = -1
        is_root = pos <= 0 and self.records[record] == self.general.__class__
        if pos <= 0 and not is_root:  # new record
            res = self._add_record(record, data)
            if res:
                return res
        else:
            if is_root:
                clazz = self.general.__class__
                recset = None
                key = None
            else:
                table = record[:pos]
                recset = getattr(self.general, self.records[table].path)
                key = record[pos + 1:]
                if key not in recset:
                    return {
                        'action': 'error',
                        'message': 'Unknown ' + table + ' "' + key + '"'}
                clazz = self.records[table]
            rec = recset[key] if not is_root else self.general
            res = _change_record(clazz, rec, data, recset, key)
            if res:
                return res
        if self.file:
            self.general.output(self.file)
        return show

    def record_form(self, record):
        """Create a HTML form for this record"""
        pos = record.find("/")
        add = False
        if pos <= 0 or pos == len(record) - 1:
            if pos > 0:
                record = record[:pos]
            if record not in self.records:
                return '<h1>Unknown record "' + record + '"</h1>'
            rec = self.records[record](self.general)
            add = True
        else:
            table = record[:pos]
            key = record[pos + 1:]
            if table not in self.records:
                return '<h1>Unknown record "' + table + '"</h1>'
            records = getattr(self.general, self.records[table].path)
            if key not in records:
                return '<h1>Unknown ' + table + ' "' + key + '"</h1>'
            rec = records[key]
        return form.form(rec, ("Add " if add else "Edit ") + rec.get_name())

    def field_info(self, table):
        """Show the known information about the fields of this record"""
        fields = []
        for fld in self.records[table].fields:
            if isinstance(fld, Set):
                continue
            info = field_values(fld, self.general)
            fields.append(info)
        return fields

    def call(self, url, data):
        """Match the url and call the different corresponding routines"""
        try:
            if url in ['/fields/', '/fields', '/record', '/record/']:
                res = layout(self.show_table())
            elif url.startswith("/fields/"):
                res = layout(self.field_info(url[8:]))
            elif url.startswith('/record/'):
                res = layout(self.record_info(url[8:]))
            elif url.startswith('/delete/'):
                res = layout(self.record_delete(url[8:]))
            elif url.startswith('/write/'):
                res = layout(self.record_write(url[7:], data))
            elif url.startswith('/form/'):
                res = self.record_form(url[6:])
            elif url.startswith('/list/'):
                res = self.list_records(url[6:], data)
            else:
                res = layout(show_documentation())
            return res
        except KeyError as e:
            show = {
                'action': 'error',
                'message': 'Unknown table "' + e.args[0] + '"'}
            return layout(show)
        except ValueError as e:
            show = {
                'action': 'error',
                'message': e.args[0]}
            return layout(show)

    def handler(self, ws, path):
        """Handle requests from the websocket server"""
        if path == "/":
            lines = yield from ws.recv().split("/n")
            result = self.call(lines[0], lines[1] if len(lines) > 1 else "")
            yield from ws.send(result)
        else:
            yield from ws.send("Unknown url: " + path)

    def start(self):
        """Start the websocket server"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        server = serve(self.handler, 'localhost', 8080)
        self.server = self.loop.run_until_complete(server)
        self.loop.run_forever()
