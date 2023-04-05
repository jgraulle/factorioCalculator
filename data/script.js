function getSortValue(table, rowIndex, columnIndex)
{
    return table.tBodies[0].rows[rowIndex].getElementsByTagName("td")[columnIndex].getAttribute("data-sort")
}

function sortTable(tableId, columnIndex)
{
    var table = document.getElementById(tableId);
    direction = 0
    if (table.hasAttribute("data-sort-column") && table.hasAttribute("data-sort-direction"))
    {
        if (columnIndex == table.getAttribute("data-sort-column") && table.getAttribute("data-sort-direction") == 0)
            direction = -1
    }
    // First row is table header
    var isMoved = true
    while (isMoved)
    {
        isMoved = false
        for (rowIndex = 0; rowIndex < table.tBodies[0].rows.length-1; ++rowIndex)
        {
            var sortValue1 = getSortValue(table, rowIndex, columnIndex)
            var sortValue1AsFloat = parseFloat(sortValue1)
            var sortValue2 = getSortValue(table, rowIndex+1, columnIndex)
            var sortValue2AsFloat = parseFloat(sortValue2)
            if (!isNaN(sortValue1AsFloat) && !isNaN(sortValue2AsFloat))
            {
              sortValue1 = sortValue1AsFloat
              sortValue2 = sortValue2AsFloat
            }
            if ((sortValue1>sortValue2 && direction==0) || (sortValue1<sortValue2 && direction==-1))
            {
                table.tBodies[0].rows[rowIndex].parentNode.insertBefore(table.tBodies[0].rows[rowIndex+1], table.tBodies[0].rows[rowIndex]);
                isMoved = true
            }
        }
    }
    table.setAttribute("data-sort-column", columnIndex)
    table.setAttribute("data-sort-direction", direction)
}
