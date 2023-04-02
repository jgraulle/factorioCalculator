function getSortValue(table, rowIndex, columnIndex)
{
    return table.rows[rowIndex].getElementsByTagName("td")[columnIndex].getAttribute("data-sort")
}

function sortTable(columnIndex)
{
    var table = document.getElementById("mainTable");
    direction = 0
    if (table.hasAttribute("data-sort-column") && table.hasAttribute("data-sort-direction"))
    {
        if (columnIndex == table.getAttribute("data-sort-column") && table.getAttribute("data-sort-direction") == 0)
            direction = -1
    }
    // First row is table header, last row is total
    var isMoved = true
    while (isMoved)
    {
        isMoved = false
        for (rowIndex = 1; rowIndex < table.rows.length-2; ++rowIndex)
        {
            var sortValue1 = parseFloat(getSortValue(table, rowIndex, columnIndex))
            var sortValue2 = parseFloat(getSortValue(table, rowIndex+1, columnIndex))
            if ((sortValue1>sortValue2 && direction==0) || (sortValue1<sortValue2 && direction==-1))
            {
                table.rows[rowIndex].parentNode.insertBefore(table.rows[rowIndex+1], table.rows[rowIndex]);
                isMoved = true
            }
        }
    }
    table.setAttribute("data-sort-column", columnIndex)
    table.setAttribute("data-sort-direction", direction)
}
