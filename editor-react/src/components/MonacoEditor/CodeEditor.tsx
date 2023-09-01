import { FC, useEffect, useRef, useState } from "react";
import MonacoEditor from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import { editor } from "monaco-editor";
import prettier from "prettier";
import parser from "prettier/parser-babel";
import { optionsProgrammingLanguage } from "@/libs/constants";
import { SearchSelectCommand } from "../SearchCommand/SearchCommand";
import { IoMdArrowDropdown } from "react-icons/io";
import { Badge } from "../ui/badge";

const heightExtraSpace = 30;

type Monaco = typeof monaco;

type OnMountType = (
  editor: editor.IStandaloneCodeEditor,
  monaco: Monaco
) => void;

type OnChangeType = (
  value: string | undefined,
  ev: editor.IModelContentChangedEvent
) => void;

interface CodeEditorProps {
  codeDataProp: {
    codeValue: string;
    linesCount: number;
  };
  onChange?: (value: string, linesCount: number) => void;
  isEditable?: boolean;
}

const CodeEditor: FC<CodeEditorProps> = ({
  codeDataProp,
  onChange,
  isEditable = true,
}) => {
  const editorRef = useRef<editor.IStandaloneCodeEditor>(null);

  const [height, setHeight] = useState(400);

  const [selectedLanguage, setSelectedLanguage] = useState(
    optionsProgrammingLanguage[1]
  );
  const [openStateLanguageSelect, setOpenStateLanguageSelect] =
    useState<boolean>(false);

  useEffect(() => {
    editorRef.current &&
      editorRef.current.updateOptions({
        readOnly: !isEditable,
        padding: { top: 10, bottom: 10 },
      });
  }, [isEditable]);

  const handleLanguageSelect = (selectedLanguage: {
    label: string;
    value: string;
  }) => {
    setSelectedLanguage(selectedLanguage);
  };

  const handleEditorDidMount: OnMountType = (editor) => {
    editorRef.current = editor;
    editor.getModel()?.updateOptions({
      tabSize: 2,
    });
    editorRef.current.updateOptions({
      readOnly: !isEditable,
      padding: { top: 13, bottom: 10 },
    });
    const linesCount = editorRef.current.getModel().getLineCount();
    const heightValue = linesCount * heightExtraSpace;
    setHeight(heightValue);
  };

  const handleEditorChange: OnChangeType = (value, editor) => {
    const linesCount = editorRef.current.getModel().getLineCount();
    const heightValue = linesCount * heightExtraSpace;
    setHeight(heightValue <= 600 ? heightValue : 600);
    if (value !== undefined && onChange) {
      onChange(value, linesCount);
    }
  };

  // const onFormatClick = async () => {
  //   // //get the current value from the editor
  //   // const unformatted = editorRef.current.getModel().getValue();
  //   // console.log({ unformatted });
  //   // //format the value
  //   // const formatted = await prettier.format(unformatted, {
  //   //   parser: "babel",
  //   //   plugins: [parser],
  //   //   useTabs: false,
  //   // });
  //   // //set the formatted value back in the editor
  //   // if (formatted) {
  //   //   console.log({ formatted });
  //   //   editorRef.current.setValue(formatted.replace(/\n$/, ""));
  //   // }
  // };

  // try {
  //   const test = async () => {
  //     const code = `function add(a, b) {
  //             return a + b;
  //           }`;

  //     // const prettier = await import("prettier/standalone");
  //     // const babylon = await import('prettier/parser-babylon');
  //     // const babel = await import("prettier/parser-babel");
  //     // window.nigga = prettier;

  //     const formattedCode = await prettier.format(code, {
  //       parser: "babel",
  //       plugins: [parser],
  //       semi: true,
  //       useTabs: false,
  //     });

  //     console.log({ formattedCode });
  //   };
  //   test();
  // } catch (e) {
  //   console.log({ e });
  // }

  return (
    <div className="h-full flex flex-col gap-sm">
      <SearchSelectCommand
        open={openStateLanguageSelect}
        setOpen={setOpenStateLanguageSelect}
        options={optionsProgrammingLanguage}
        getSelectedValue={handleLanguageSelect}
      />
      {/* top bar of code editor */}
      <div className="flex gap-sm md:gap-md">
        {isEditable && (
          <div
            className="bg-primary dark:bg-primary-foreground text-input text-sm rounded-md w-32 overflow-hidden flex gap-2 justify-between items-center py-1 px-2"
            onClick={() => setOpenStateLanguageSelect((prev) => !prev)}
          >
            {selectedLanguage.label}
            <IoMdArrowDropdown className="h-4 w-4" />
          </div>
        )}
        {!isEditable && (
          <Badge className="py-1" variant={"outline"}>
            {selectedLanguage?.label}
          </Badge>
        )}
      </div>
      <div
        className={`relative h-full group border border-3 border-primary border-opacity-50 ${
          !isEditable && "pointer-events-none md:pointer-events-auto"
        }`}
      >
        {/* <Button
          className="absolute top-0 right-0 z-10 invisible group-hover:visible"
          onClick={onFormatClick}
        >
          Format
        </Button> */}
        <MonacoEditor
          value={codeDataProp?.codeValue}
          onMount={handleEditorDidMount}
          onChange={handleEditorChange}
          theme="vs-dark"
          language={selectedLanguage.value}
          height={height}
          options={{
            wordWrap: "on",
            minimap: { enabled: false },
            folding: false,
            lineNumbersMinChars: 3,
            fontSize: 16,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            formatOnPaste: true,
          }}
        />
      </div>
    </div>
  );
};

export default CodeEditor;
