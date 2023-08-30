import CodeEditor from "@/components/MonacoEditor/CodeEditor";
import { useState } from "react";

const MonacoEditorPage = () => {
  const initialEditorValue = `//write some amazing code here \n//Explain precisely \n//Max line you get is 15 `;

  const [CodeEditorData, setCodeEditorData] = useState<{
    codeValue: string;
    linesCount: number;
  }>({
    codeValue: initialEditorValue,
    linesCount: 1,
  });

  const handleCodeEditorChange = (value: string, linesCount: number) => {
    setCodeEditorData({ codeValue: value, linesCount: linesCount });
  };

  return (
    <div className="flex  flex-col gap-md">
      <h2>MonacoEditorPage</h2>
      <div className="h-[60dvh] border-3">
        <CodeEditor
          codeDataProp={CodeEditorData}
          onChange={handleCodeEditorChange}
        />
        {CodeEditorData.linesCount > 15 && (
          <p className="text-destructive">Number of lines of code must be less than or equal to 15</p>
        )}
      </div>
    </div>
  );
};

export default MonacoEditorPage;
