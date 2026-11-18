"""Resolve HTML table spans and column widths for PDF rendering."""

from core.document_engine.formatting import inline_style, points


def _span(cell, attribute, limit):
    value = cell.get(attribute, "1")
    if value.isascii() and value.isdecimal() and len(value) <= 4:
        return max(1, min(limit, int(value)))
    return 1


def table_layout(table, available_width):
    rows = table.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")
    columns = table.xpath("./col|./colgroup/col")
    placements = []
    occupied_until = []
    for row, element in enumerate(rows):
        column = 0
        for cell in element.xpath("./td|./th"):
            across = _span(cell, "colspan", 63)
            down = _span(cell, "rowspan", len(rows) - row)
            while any(end > row for end in occupied_until[column:column + across]):
                column += 1
            end = column + across
            occupied_until.extend([0] * (end - len(occupied_until)))
            occupied_until[column:end] = [row + down] * across
            placements.append((cell, row, column, across, down))
            column = end
    count = max(len(occupied_until), len(columns))
    if not placements:
        return [], len(rows), placements
    specified = [points(inline_style(column).get("width")) for column in columns]
    known = [width for width in specified if width is not None]
    fallback = sum(known) / len(known) if known else available_width / count
    widths = [(specified[i] if i < len(specified) else None) or fallback for i in range(count)]
    scale = min(1, available_width / sum(widths))
    return [width * scale for width in widths], len(rows), placements
