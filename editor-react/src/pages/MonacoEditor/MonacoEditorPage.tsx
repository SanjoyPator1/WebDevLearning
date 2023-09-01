import CodeEditor from "@/components/MonacoEditor/CodeEditor";
import { Button } from "@/components/ui/button";
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

  const [isEditable, setIsEditable] = useState(true);

  const handleCodeEditorChange = (value: string, linesCount: number) => {
    setCodeEditorData({ codeValue: value, linesCount: linesCount });
  };

  return (
    <div className="flex  flex-col gap-md">
      <h2>MonacoEditorPage</h2>
      <Button onClick={() => setIsEditable((prev) => !prev)} className="w-fit">
        {isEditable ? "View Only" : "Edit"}
      </Button>
      <div className="h-fit flex flex-col gap-base">
        <CodeEditor
          codeDataProp={CodeEditorData}
          onChange={handleCodeEditorChange}
          isEditable={isEditable}
        />
        {CodeEditorData.linesCount > 15 && (
          <p className="text-destructive">
            Number of lines of code must be less than or equal to 15
          </p>
        )}
      </div>
    </div>
  );
};

export default MonacoEditorPage;
