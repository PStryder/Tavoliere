import { useContext } from "react";
import { TableContext, type TableContextValue } from "../state/TableContext";

export function useTable(): TableContextValue {
  const ctx = useContext(TableContext);
  if (!ctx) throw new Error("useTable must be used within TableProvider");
  return ctx;
}
