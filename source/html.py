"""Routines to efficiently export to HTML"""
import io

from enum import Enum
from fields import Relation

CURRENT = None


def write(*values):
    """Write a set of values to the current HTML file"""
    for value in values:
        CURRENT.write(str(value))


def file(name, title):
    """Start a new html file"""
    global CURRENT
    if CURRENT:
        finish()
    CURRENT = open(name, 'w')
    page_header(title)


def page_header(title):
    """Show the page header"""
    write('<!DOCTYPE HTML>\n')
    write('<html>\n')
    write('<head>\n')
    write('  <meta charset="UTF-8">\n')
    write('  <title>', title, '</title>\n')
    write('  <link rel="stylesheet" href="jquery/jquery-ui.css">\n')
    write('  <script src="jquery/jquery.js"></script>\n')
    write('  <script src="jquery/jquery-ui.min.js"></script>\n')
    write('  <script src="forms.js"></script>\n')
    write('  <link rel="stylesheet" type="text/css" href="theme.css">\n')
    write('</head>\n')
    write('<body>\n')


def page_footer():
    """Show the page footer, close it and return the whole page content"""
    global CURRENT
    write('</body>\n</html>')
    res = CURRENT.getvalue()
    CURRENT.close()
    CURRENT = None
    return res


def serving():
    """Start a html page that will be returned by the server"""
    global CURRENT
    if CURRENT:
        finish()
    CURRENT = io.StringIO()


def page(title):
    """Write the header of a html page"""
    write('<h1>', title, '</h1>\n')


def finish(show_result=False):
    """Finish writing to the current HTML file"""
    global CURRENT
    write("<script>\n")
    write('$("button").button({icons:{primary:"ui-icon-edit"},text:false});\n')
    write("</script>")
    if show_result:
        res = CURRENT.getvalue()
        CURRENT.close()
        CURRENT = None
        return res
    write('\n</body>\n')
    write('</html>')
    CURRENT.close()
    CURRENT = None


def edit(rec, rid):
    """Show an edit button"""
    out = '<button onclick="edit(event, \'' + rec + '\', \'' + rid + '\')">'
    out += 'edit ' + rec + '/' + rid + '</button>'
    return out


def table(*names):
    """Start a table"""
    write("<table>\n")
    headers(*names)


def headers(*names):
    """Write headers to a table"""
    write("<tr>")
    for name in names:
        write("<th>", name, "</th>")
    write("</tr>\n")


class DType(Enum):
    """Type of detail table line"""
    header = 1
    total = 2
    normal = 3


def detail(dtype, *values):
    """Show detail records"""
    if dtype == DType.total:
        write('<tr class="total">')
    else:
        write('<tr>')
    first = True
    for value in values:
        if dtype == DType.header and first:
            write('<th>', value, '</th>')
        elif value.endswith('#'):
            write('<td class="amount">', value[:-1], '</td>')
        else:
            write('<td>', value, '</td>')
        first = False
    write('</tr>\n')


def link(text, href):
    """Return link"""
    return '<a href="' + href + '">' + str(text) + '</a>'


def create_link(rec, fld, fldexpr, pos):
    """Create a link from a given expression"""
    if isinstance(rec.field(fld), Relation):
        val = getattr(rec, fld)
    else:
        val = rec
    expr = fldexpr[pos + 1:]
    replfrom = expr.find('[')
    repltill = expr.find(']')
    if val:
        lpart = getattr(val, expr[replfrom + 1:repltill])
        write('<a href="', expr[:replfrom], lpart, expr[repltill + 1:], '">')


def line(rec, *fields):
    """Write a line to the table"""
    write("<tr>")
    first = True
    ebt = edit(rec.get_name(), rec.get_id())
    for fldexpr in fields:
        pos = fldexpr.find("#")
        if first:
            write("<th>" + ebt)
        else:
            if pos + 1 == len(fldexpr):
                write('<td class="amount">')
            else:
                write('<td>')

        if pos > 0:
            fld = fldexpr[:pos]
            if pos < len(fldexpr) - 1:
                create_link(rec, fld, fldexpr, pos)
        else:
            fld = fldexpr
        val = getattr(rec, fld)
        write(rec.field(fld).show(val) if val else '')
        if 0 < pos < len(fldexpr) - 1:
            write("</a>")
        if first:
            write("</th>\n")
            first = False
        else:
            write("</td>")
    write("</tr>\n")


def table_finish():
    """Stop the current table"""
    write("</table>")
