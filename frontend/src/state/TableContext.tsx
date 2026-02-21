import {
  createContext,
  useReducer,
  type ReactNode,
  type Dispatch,
} from "react";
import {
  tableReducer,
  initialTableState,
  type TableContextState,
  type TableAction,
} from "./reducers";

export interface TableContextValue {
  state: TableContextState;
  dispatch: Dispatch<TableAction>;
}

export const TableContext = createContext<TableContextValue | null>(null);

export function TableProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(tableReducer, initialTableState);

  return (
    <TableContext.Provider value={{ state, dispatch }}>
      {children}
    </TableContext.Provider>
  );
}
