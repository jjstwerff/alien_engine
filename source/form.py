"""Code to show a form in HTML"""
from html import serving, write, page_header, page_footer
from fields import Date, Amount, Number, Enum, Relation


def form(rec, title):
    """Generate HTML content for a general form"""
    root = rec.data_store.root
    serving()
    page_header(title)
    write('<form action="" method="post" id="form"><table>')
    has_date = False
    for fld in rec.fields:
        val = getattr(rec, fld.name, None)
        write('<tr><th>', fld.name, '</th><td class="buttons">')
        inp = '<input name="' + fld.name + '"'
        if val:
            inp += ' value="' + str(val) + '"'
        if isinstance(fld, Date):
            write(inp, ' class="datepicker" size=7>')
            has_date = True
        elif isinstance(fld, Amount) or isinstance(fld, Number):
            write(inp, ' size=8>')
        elif isinstance(fld, Enum):
            write('<select name="', fld.name, '">\n')
            elm = 1
            for value in fld.values:
                sel = 'selected' if elm == val else ''
                write(
                    '<option value="' + value + '"', sel, '>', value,
                    '</option>\n')
                elm += 1
            write('</select>\n')
        elif isinstance(fld, Relation):
            write('<select name="' + fld.name + '">\n')
            ls = []
            if fld.allow_null:
                ls.append(('', ''))
            for rec in getattr(root, fld.related.path):
                ls.append((rec.get_id(), rec.show()))
            for key, value in ls:
                sel = 'selected' if key == val else ''
                write(
                    '<option value="' + key + '"', sel + '>', value,
                    '</option>\n')
            write('</select>\n')
        else:
            write(inp, '>')
        write('</td></tr>\n')
    write('<tr><td class="buttons">')
    write('<input type="submit" value="ok"></td>\n')
    write('<td class="buttons">')
    write(
        '<input type="button" value="cancel" style="float:right"' +
        ' onclick="self.close();">')
    write('</td></tr>\n')
    write('</table></form>')
    write("<script>\n")
    if has_date:
        write(
            '$(function() {$( ".datepicker" ).' +
            'datepicker({ dateFormat: "yy-mm-dd" });});\n')
    write(
        '$( "#form" ).submit(function( event ) {\n' +
        'json_form("' + rec.get_name() + '", "' + rec.get_key() +
        '", $( this ).serializeArray());\n' +
        'event.preventDefault();});\n')
    write("</script>\n")
    return page_footer()
