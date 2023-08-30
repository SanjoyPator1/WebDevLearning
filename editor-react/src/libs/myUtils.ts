import { Dispatch, SetStateAction, createContext } from "react";

type ContextType = {
    height: number;
    setHeight: Dispatch<SetStateAction<number>>;
  };
  
  export const EditorHeightContext = createContext<ContextType>({
    height: 200,
    setHeight: () => {}
  });