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
import { ChevronDown, ChevronUp, Search, Download } from "lucide-react";
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
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

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

  return (
    <div
      className={clsx(
        "bg-white rounded-lg border border-gray-200 overflow-hidden",
        compact ? "shadow-sm table-compact" : "shadow-sm",
        className
      )}
    >
      {/* Header */}
      {(title || searchable || exportable) && (
        <div
          className={clsx(
            "border-b border-gray-200 bg-gray-50",
            compact ? "p-2" : "p-3"
          )}
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              {title && (
                <h3 className="text-base font-semibold text-gray-900 truncate">
                  {title}
                </h3>
              )}
            </div>
            <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-2">
              {searchable && (
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-gray-400 w-3.5 h-3.5" />
                  <input
                    value={globalFilter ?? ""}
                    onChange={(e) => setGlobalFilter(String(e.target.value))}
                    className={clsx(
                      "w-full sm:w-auto pl-8 pr-3 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500",
                      compact ? "search-input" : "py-1.5"
                    )}
                    placeholder={searchPlaceholder}
                  />
                </div>
              )}
              {exportable && onExport && (
                <button
                  onClick={onExport}
                  className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
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
      <div className="overflow-x-auto">
        <table className="w-full min-w-full">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={clsx(
                      "text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-200 last:border-r-0 whitespace-nowrap",
                      compact ? "px-1.5 py-1.5" : "px-2 py-2",
                      header.column.columnDef.meta?.className
                    )}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={clsx(
                          "flex items-center gap-2",
                          header.column.getCanSort()
                            ? "cursor-pointer select-none hover:text-gray-700"
                            : ""
                        )}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getCanSort() && (
                          <span className="text-gray-400">
                            {header.column.getIsSorted() === "desc" ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : header.column.getIsSorted() === "asc" ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <div className="w-4 h-4 flex flex-col items-center justify-center">
                                <ChevronUp className="w-3 h-2 -mb-1" />
                                <ChevronDown className="w-3 h-2" />
                              </div>
                            )}
                          </span>
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
                    "text-center text-gray-500",
                    compact ? "px-2 py-3" : "px-2 py-4"
                  )}
                >
                  No data available
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={clsx(
                        "text-sm text-gray-900 border-r border-gray-200 last:border-r-0",
                        compact ? "px-1.5 py-1.5" : "px-2 py-2",
                        cell.column.columnDef.meta?.className
                      )}
                    >
                      <div className="min-w-0 overflow-hidden">
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
            compact ? "px-2 py-2" : "px-3 py-2.5"
          )}
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between overflow-hidden">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
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
                <div className="flex items-center gap-1.5 text-center sm:text-left bg-white px-2 py-1 rounded-md border border-gray-200">
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
                      "border border-gray-300 rounded-md bg-white text-gray-700 hover:border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500/20 transition-all duration-200 cursor-pointer",
                      compact
                        ? "page-size-selector"
                        : "px-2 py-1 text-xs min-w-[50px]"
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
                "flex items-center justify-center mt-2 sm:mt-0",
                compact ? "pagination-compact" : "gap-1"
              )}
            >
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className={clsx(
                  "font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors",
                  compact ? "pagination-button" : "px-2 py-1 text-xs"
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
                          "font-medium rounded-md transition-colors text-center",
                          compact
                            ? "pagination-button min-w-[24px]"
                            : "px-2 py-1 text-xs min-w-[28px]",
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
                  "font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors",
                  compact ? "pagination-button" : "px-2 py-1 text-xs"
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
