import {MantineReactTable, useMantineReactTable} from "mantine-react-table";
import {useMemo} from "react";

import { ReadableStream } from "web-streams-polyfill/polyfill";
if (typeof globalThis.ReadableStream === "undefined") {
  globalThis.ReadableStream = ReadableStream;
}

function TableResult({data}) {
  const columns = useMemo(
    () => Object.keys(data[0]).map((d) => ({accessorKey: d, header: d})),
    [],
  );
  const table = useMantineReactTable({
    columns,
    data,
  });
  return (
    <div>
      <MantineReactTable table={table} />
    </div>
  );
}

export default TableResult;
