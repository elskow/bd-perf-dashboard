import React from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { useState, useEffect } from "react";
import { ChevronDown, Search, Download, X, Filter, Check } from "lucide-react";
import clsx from "clsx";

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData, TValue> {
    className?: string;
  }
}

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  title?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  exportable?: boolean;
  onExport?: () => void;
  className?: string;
  pageSize?: number;
  showPagination?: boolean;
  compact?: boolean;
  showPageSizeSelector?: boolean;
  pageSizeOptions?: number[];
  initialSorting?: SortingState;
  filterable?: boolean;
  filterableColumns?: string[];
  onFilterClick?: (column: string, value: string) => void;
}

export function DataTable<T>({
  data,
  columns,
  title,
  searchable = false,
  searchPlaceholder = "Search...",
  exportable = false,
  onExport,
  className = "",
  pageSize = 10,
  showPagination = true,
  compact = false,
  showPageSizeSelector = true,
  pageSizeOptions = [5, 10, 20, 50, 100],
  initialSorting = [],
  filterable = false,
  filterableColumns = [],
  onFilterClick,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [activeFilters, setActiveFilters] = useState<
    Array<{ column: string; value: string }>
  >([]);
  const [openFilterDropdown, setOpenFilterDropdown] = useState<string | null>(
    null
  );

  const getStoredPageSize = () => {
    try {
      const stored = localStorage.getItem("dataTable-pageSize");
      if (stored && pageSizeOptions.includes(Number(stored))) {
        return Number(stored);
      }
    } catch (error) {
      console.warn("Failed to load page size from localStorage:", error);
    }
    return pageSize;
  };

  const [currentPageSize, setCurrentPageSize] = useState(getStoredPageSize);

  // Handle keyboard events for dropdown
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && openFilterDropdown) {
        setOpenFilterDropdown(null);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openFilterDropdown]);

  // Custom filter function for multi-value column filters
  const customColumnFilter = (row: any, columnId: string, filterValue: any) => {
    if (
      !filterValue ||
      !Array.isArray(filterValue) ||
      filterValue.length === 0
    ) {
      return true;
    }

    const cellValue = row.getValue(columnId);
    return filterValue.includes(cellValue);
  };

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    filterFns: {
      multiValue: customColumnFilter,
    },
    sortingFns: {
      customDateSort: (rowA, rowB, columnId) => {
        const a = rowA.getValue(columnId) as string;
        const b = rowB.getValue(columnId) as string;

        // Parse dates in "DD MMM" format (e.g., "15 MAR", "20 DEC")
        const parseShortDate = (dateStr: string): Date => {
          // Treat empty/dash values as very old dates (oldest possible)
          if (!dateStr || dateStr === "-" || dateStr.trim() === "") {
            return new Date(1900, 0, 1); // January 1, 1900
          }

          try {
            const [day, month] = dateStr.split(" ");
            const monthMap: Record<string, number> = {
              JAN: 0,
              FEB: 1,
              MAR: 2,
              APR: 3,
              MAY: 4,
              JUN: 5,
              JUL: 6,
              AUG: 7,
              SEP: 8,
              OCT: 9,
              NOV: 10,
              DEC: 11,
            };

            const monthIndex = monthMap[month?.toUpperCase()];
            if (monthIndex !== undefined && day) {
              const currentYear = new Date().getFullYear();
              return new Date(currentYear, monthIndex, parseInt(day));
            }
          } catch (error) {
            return new Date(1900, 0, 1); // Fallback to old date
          }

          return new Date(1900, 0, 1); // Fallback to old date
        };

        const dateA = parseShortDate(a);
        const dateB = parseShortDate(b);

        // Compare dates - empty dates will naturally sort as oldest
        return dateA.getTime() - dateB.getTime();
      },
    },
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    initialState: {
      pagination: {
        pageSize: currentPageSize,
      },
    },
  });

  useEffect(() => {
    try {
      localStorage.setItem("dataTable-pageSize", currentPageSize.toString());
    } catch (error) {
      console.warn("Failed to save page size to localStorage:", error);
    }
  }, [currentPageSize]);

  const handleFilterClick = (column: string, value: string) => {
    if (!filterable || !onFilterClick) return;

    // Check if filter already exists
    const existingFilter = activeFilters.find(
      (f) => f.column === column && f.value === value
    );
    if (existingFilter) return;

    // Add new filter
    const newFilter = { column, value };
    setActiveFilters((prev) => [...prev, newFilter]);

    // Update column filters for the table
    const existingColumnFilter = columnFilters.find((f) => f.id === column);
    if (existingColumnFilter) {
      // Add to existing filter values
      const currentValues = Array.isArray(existingColumnFilter.value)
        ? existingColumnFilter.value
        : [existingColumnFilter.value];
      setColumnFilters((prev) =>
        prev.map((f) =>
          f.id === column ? { ...f, value: [...currentValues, value] } : f
        )
      );
    } else {
      // Create new column filter
      setColumnFilters((prev) => [...prev, { id: column, value: [value] }]);
    }

    onFilterClick(column, value);
  };

  const removeFilter = (column: string, value: string) => {
    // Remove from active filters
    setActiveFilters((prev) =>
      prev.filter((f) => !(f.column === column && f.value === value))
    );

    // Update column filters
    const columnFilter = columnFilters.find((f) => f.id === column);
    if (columnFilter) {
      const currentValues = Array.isArray(columnFilter.value)
        ? columnFilter.value
        : [columnFilter.value];
      const newValues = currentValues.filter((v) => v !== value);

      if (newValues.length === 0) {
        // Remove entire column filter if no values left
        setColumnFilters((prev) => prev.filter((f) => f.id !== column));
      } else {
        // Update with remaining values
        setColumnFilters((prev) =>
          prev.map((f) => (f.id === column ? { ...f, value: newValues } : f))
        );
      }
    }
  };

  const clearAllFilters = () => {
    setActiveFilters([]);
    setColumnFilters([]);
  };

  // Get unique values for a column
  const getColumnUniqueValues = (columnId: string) => {
    const values = data
      .map((row: any) => row[columnId])
      .filter((value) => value && value !== "-")
      .filter((value, index, array) => array.indexOf(value) === index)
      .sort();
    return values;
  };

  // Get active filter values for a column
  const getActiveFilterValues = (columnId: string) => {
    const filter = columnFilters.find((f) => f.id === columnId);
    return filter && Array.isArray(filter.value) ? filter.value : [];
  };

  // Toggle filter value
  const toggleFilterValue = (columnId: string, value: string) => {
    const currentValues = getActiveFilterValues(columnId);
    const isActive = currentValues.includes(value);

    if (isActive) {
      // Remove value
      removeFilter(columnId, value);
    } else {
      // Add value
      handleFilterClick(columnId, value);
    }

    // Close dropdown after applying filter
    setOpenFilterDropdown(null);
  };

  return (
    <div
      className={clsx(
        "bg-white rounded-lg border border-gray-200 overflow-hidden",
        compact ? "shadow-sm table-compact" : "shadow-sm",
        "responsive-table",
        className
      )}
    >
      {/* Header */}
      {(title || searchable || exportable) && (
        <div
          className={clsx(
            "border-b border-gray-200 bg-gray-50",
            compact ? "p-2 sm:p-3" : "p-3 sm:p-4"
          )}
        >
          <div className="flex flex-col gap-3 sm:gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
              {title && (
                <h3 className="text-sm sm:text-base font-medium text-gray-900 truncate tracking-wide">
                  {title}
                </h3>
              )}
              {/* Active Filters Count */}
              {filterable && activeFilters.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  <span className="inline-flex items-center gap-1 px-2 sm:px-2.5 py-0.5 sm:py-1 bg-red-100 text-red-700 text-xs font-normal italic rounded-full">
                    <Filter className="w-3 h-3" />
                    {activeFilters.length} filter
                    {activeFilters.length > 1 ? "s" : ""}
                  </span>
                  <button
                    onClick={clearAllFilters}
                    className="text-xs text-gray-600 hover:text-red-600 font-normal underline decoration-dotted transition-colors touch-target"
                  >
                    Clear all
                  </button>
                </div>
              )}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-2">
              {searchable && (
                <div className="relative w-full sm:w-auto">
                  <input
                    value={globalFilter ?? ""}
                    onChange={(e) => setGlobalFilter(String(e.target.value))}
                    className={clsx(
                      "w-full sm:w-64 pl-10 pr-3 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 touch-target",
                      compact ? "search-input py-2.5" : "py-2.5"
                    )}
                    placeholder={searchPlaceholder}
                  />
                </div>
              )}
              {exportable && onExport && (
                <button
                  onClick={onExport}
                  className="flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors touch-target"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Export</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div
        className="overflow-x-auto scrollbar-hide -webkit-overflow-scrolling-touch"
        onClick={(e) => {
          // Close dropdown when clicking outside
          if (!(e.target as Element).closest(".filter-dropdown-container")) {
            setOpenFilterDropdown(null);
          }
        }}
      >
        <table className="w-full min-w-max">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={clsx(
                      "text-center text-xs font-normal text-gray-600 uppercase tracking-wider border-r border-gray-200 last:border-r-0 relative whitespace-nowrap",
                      compact
                        ? "px-2 sm:px-3 py-2 sm:py-2.5"
                        : "px-3 sm:px-4 py-2.5 sm:py-3",
                      header.column.columnDef.meta?.className,
                      // Define responsive column widths for scrollable table
                      header.column.id === "name" &&
                        "w-[160px] sm:w-[180px] max-w-[160px] sm:max-w-[180px]",
                      header.column.id === "industry" &&
                        "min-w-[100px] sm:min-w-[120px]",
                      header.column.id === "stage" &&
                        "min-w-[100px] sm:min-w-[120px]",
                      header.column.id === "expected_revenue" &&
                        "min-w-[90px] sm:min-w-[100px]",
                      header.column.id === "probability" &&
                        "min-w-[70px] sm:min-w-[80px]",
                      header.column.id === "meeting_count" &&
                        "min-w-[70px] sm:min-w-[80px]",
                      header.column.id === "first_meeting_date" &&
                        "min-w-[90px] sm:min-w-[100px]",
                      header.column.id === "warm_focus_date" &&
                        "min-w-[90px] sm:min-w-[100px]"
                    )}
                  >
                    {header.isPlaceholder ? null : (
                      <div className="flex items-center gap-2 h-6 relative filter-dropdown-container">
                        <div
                          className={clsx(
                            "flex items-center gap-1 flex-1 min-w-0",
                            header.column.getCanSort()
                              ? "cursor-pointer select-none hover:text-gray-700"
                              : ""
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <span>
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                          </span>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {filterable &&
                              filterableColumns.includes(header.column.id) && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setOpenFilterDropdown(
                                      openFilterDropdown === header.column.id
                                        ? null
                                        : header.column.id
                                    );
                                  }}
                                  className="text-gray-400 hover:text-gray-600 p-1 touch-target"
                                >
                                  <Filter
                                    className={clsx(
                                      "w-3 h-3",
                                      getActiveFilterValues(header.column.id)
                                        .length > 0
                                        ? "text-red-600"
                                        : ""
                                    )}
                                  />
                                  {getActiveFilterValues(header.column.id)
                                    .length > 0 && (
                                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                                  )}
                                </button>
                              )}
                            {header.column.getCanSort() && (
                              <span className="text-gray-400">
                                {header.column.getIsSorted() === "desc" ? (
                                  <ChevronDown className="w-3 h-3" />
                                ) : header.column.getIsSorted() === "asc" ? (
                                  <ChevronDown className="w-3 h-3 rotate-180" />
                                ) : (
                                  <div className="w-3 h-3 flex flex-col items-center justify-center opacity-50">
                                    <ChevronDown className="w-2 h-1 -mb-0.5" />
                                    <ChevronDown className="w-2 h-1 rotate-180" />
                                  </div>
                                )}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Filter Dropdown */}
                        {filterable &&
                          filterableColumns.includes(header.column.id) &&
                          openFilterDropdown === header.column.id && (
                            <div className="absolute top-full left-0 z-50 mt-1 w-48 sm:w-56 bg-white border border-gray-200 rounded-lg shadow-lg">
                              <div className="p-2 sm:p-3">
                                <div className="text-xs font-medium text-gray-700 mb-2 px-1 italic">
                                  Filter by {header.column.columnDef.header}
                                </div>
                                <div className="max-h-48 overflow-y-auto">
                                  {getColumnUniqueValues(header.column.id).map(
                                    (value) => {
                                      const isActive = getActiveFilterValues(
                                        header.column.id
                                      ).includes(value);
                                      return (
                                        <button
                                          key={value}
                                          onClick={() =>
                                            toggleFilterValue(
                                              header.column.id,
                                              value
                                            )
                                          }
                                          className="w-full flex items-center gap-2 px-2 py-2 sm:py-1.5 text-xs font-normal text-left hover:bg-gray-50 rounded transition-colors touch-target"
                                        >
                                          <div
                                            className={clsx(
                                              "w-4 h-4 sm:w-3 sm:h-3 border rounded flex items-center justify-center flex-shrink-0",
                                              isActive
                                                ? "border-red-500 bg-red-500"
                                                : "border-gray-300"
                                            )}
                                          >
                                            {isActive && (
                                              <Check className="w-2.5 h-2.5 sm:w-2 sm:h-2 text-white" />
                                            )}
                                          </div>
                                          <span className="flex-1 truncate text-gray-700 tracking-wide">
                                            {value}
                                          </span>
                                        </button>
                                      );
                                    }
                                  )}
                                </div>
                                {getActiveFilterValues(header.column.id)
                                  .length > 0 && (
                                  <div className="border-t border-gray-200 mt-2 pt-2">
                                    <button
                                      onClick={() => {
                                        getActiveFilterValues(
                                          header.column.id
                                        ).forEach((value) => {
                                          removeFilter(header.column.id, value);
                                        });
                                        setOpenFilterDropdown(null);
                                      }}
                                      className="w-full text-xs text-red-600 hover:text-red-700 font-normal italic py-2 sm:py-1 transition-colors touch-target"
                                    >
                                      Clear filters
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody className="bg-white divide-y divide-gray-200">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className={clsx(
                    "text-center text-gray-500 border-r-0",
                    compact ? "px-3 py-6 sm:py-4" : "px-3 py-8 sm:py-6"
                  )}
                >
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                      <Search className="w-5 h-5 text-gray-400" />
                    </div>
                    <div className="text-sm font-normal text-gray-600 italic">
                      {activeFilters.length > 0
                        ? "No data matches the current filters"
                        : "No data available"}
                    </div>
                    {activeFilters.length > 0 && (
                      <button
                        onClick={clearAllFilters}
                        className="text-xs text-red-600 hover:text-red-700 font-normal underline decoration-dotted transition-colors touch-target"
                      >
                        Clear all filters
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row, index) => (
                <tr
                  key={row.id}
                  className="hover:bg-gray-50 transition-colors border-b border-gray-100"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={clsx(
                        "text-sm text-gray-800 border-r border-gray-200 last:border-r-0 align-top whitespace-nowrap leading-snug",
                        compact
                          ? "px-2 sm:px-3 py-1.5 sm:py-2"
                          : "px-3 sm:px-4 py-2 sm:py-2.5",
                        cell.column.columnDef.meta?.className
                      )}
                    >
                      <div
                        className={clsx(
                          "min-w-0",
                          // Text alignment based on column type
                          cell.column.id === "expected_revenue" && "text-right",
                          cell.column.id === "probability" && "text-right",
                          cell.column.id === "meeting_count" && "text-center",
                          cell.column.id === "first_meeting_date" &&
                            "text-center",
                          cell.column.id === "warm_focus_date" && "text-center"
                        )}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </div>
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {showPagination && data.length > pageSize && (
        <div
          className={clsx(
            "border-t border-gray-200 bg-gray-50",
            compact
              ? "px-2 sm:px-3 py-2 sm:py-2.5"
              : "px-3 sm:px-4 py-2.5 sm:py-3"
          )}
        >
          <div className="flex flex-col gap-3 sm:gap-2 lg:flex-row lg:items-center lg:justify-between overflow-hidden">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
              <div className="text-xs text-gray-700 text-center sm:text-left min-w-0">
                Showing{" "}
                {table.getState().pagination.pageIndex *
                  table.getState().pagination.pageSize +
                  1}{" "}
                to{" "}
                {Math.min(
                  (table.getState().pagination.pageIndex + 1) *
                    table.getState().pagination.pageSize,
                  table.getFilteredRowModel().rows.length
                )}{" "}
                of {table.getFilteredRowModel().rows.length} results
              </div>
              {showPageSizeSelector && (
                <div className="flex items-center gap-1.5 text-center sm:text-left bg-white px-2 sm:px-3 py-1.5 sm:py-1 rounded-md border border-gray-200">
                  <span className="text-xs text-gray-600 hidden sm:inline">
                    Show
                  </span>
                  <select
                    value={table.getState().pagination.pageSize}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value === "all") {
                        const newSize = table.getFilteredRowModel().rows.length;
                        table.setPageSize(newSize);
                        setCurrentPageSize(newSize);
                      } else {
                        const newSize = Number(value);
                        table.setPageSize(newSize);
                        setCurrentPageSize(newSize);
                      }
                    }}
                    className={clsx(
                      "border border-gray-300 rounded-md bg-white text-gray-700 hover:border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500/20 transition-all duration-200 cursor-pointer touch-target",
                      compact
                        ? "page-size-selector py-2 sm:py-1"
                        : "px-2 sm:px-3 py-2 sm:py-1 text-xs min-w-[50px] sm:min-w-[60px]"
                    )}
                  >
                    {pageSizeOptions.map((size) => (
                      <option key={size} value={size}>
                        {size}
                      </option>
                    ))}
                    {table.getFilteredRowModel().rows.length >
                      Math.max(...pageSizeOptions) && (
                      <option value="all">
                        All ({table.getFilteredRowModel().rows.length})
                      </option>
                    )}
                  </select>
                  <span className="text-xs text-gray-600">per page</span>
                </div>
              )}
              {table.getPageCount() > 1 && (
                <div className="text-xs text-gray-500 text-center sm:text-left">
                  Page {table.getState().pagination.pageIndex + 1} of{" "}
                  {table.getPageCount()}
                </div>
              )}
            </div>
            <div
              className={clsx(
                "flex items-center justify-center mt-3 sm:mt-2 lg:mt-0",
                compact ? "pagination-compact gap-0.5" : "gap-1"
              )}
            >
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className={clsx(
                  "font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-target",
                  compact
                    ? "pagination-button py-2 sm:py-1"
                    : "px-3 sm:px-2 py-2 sm:py-1 text-xs"
                )}
              >
                <span className="hidden sm:inline">Previous</span>
                <span className="sm:hidden">‹</span>
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: table.getPageCount() }, (_, i) => i + 1)
                  .filter((page) => {
                    const current = table.getState().pagination.pageIndex + 1;
                    return (
                      page === 1 ||
                      page === table.getPageCount() ||
                      Math.abs(page - current) <= 1
                    );
                  })
                  .map((page, index, array) => (
                    <React.Fragment key={page}>
                      {index > 0 && array[index - 1] !== page - 1 && (
                        <span className="px-2 text-gray-400">...</span>
                      )}
                      <button
                        onClick={() => table.setPageIndex(page - 1)}
                        className={clsx(
                          "font-medium rounded-md transition-colors text-center touch-target",
                          compact
                            ? "pagination-button min-w-[32px] sm:min-w-[24px] py-2 sm:py-1"
                            : "px-3 sm:px-2 py-2 sm:py-1 text-xs min-w-[36px] sm:min-w-[28px]",
                          page === table.getState().pagination.pageIndex + 1
                            ? "bg-red-600 text-white"
                            : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                        )}
                      >
                        {page}
                      </button>
                    </React.Fragment>
                  ))}
              </div>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className={clsx(
                  "font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-target",
                  compact
                    ? "pagination-button py-2 sm:py-1"
                    : "px-3 sm:px-2 py-2 sm:py-1 text-xs"
                )}
              >
                <span className="hidden sm:inline">Next</span>
                <span className="sm:hidden">›</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
