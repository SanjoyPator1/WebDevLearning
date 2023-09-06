import { FC, useEffect, useRef, useState } from "react";
import MonacoEditor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import { editor } from "monaco-editor";
import prettier from "prettier";
import parser from "prettier/parser-babel";
import { monacoThemesList, optionsProgrammingLanguage } from "@/libs/constants";
import { SearchSelectCommand } from "../SearchCommand/SearchCommand";
import { IoMdArrowDropdown } from "react-icons/io";
import { Badge } from "../ui/badge";
import ComboboxComponent from "../ComboboxComponent";
import monacoThemes from "monaco-themes/themes/themelist.json";

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

  const defineTheme = (theme: string) => {
    return new Promise(async () => {
      await Promise.all([loader.init(), monacoThemesList[theme]]).then(
        ([monaco, themeData]) => {
          monaco.editor.defineTheme(
            theme,
            themeData as editor.IStandaloneThemeData
          );
          monaco.editor.setTheme(theme);
        }
      );
    });
  };

  monaco.editor;

  const [selectedTheme, setSelectedTheme] = useState({
    label: "Vs Dark",
    value: "vs-dark",
  });

  function handleThemeChange(themeChoosen: { label: string; value: string }) {
    setSelectedTheme(themeChoosen);

    if (["light", "vs-dark"].includes(themeChoosen.value)) {
      setSelectedTheme(themeChoosen);
    } else {
      defineTheme(themeChoosen.value).then(() =>
        setSelectedTheme(themeChoosen)
      );
    }
  }

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

  const handleEditorChange: OnChangeType = (value) => {
    const linesCount = editorRef.current.getModel().getLineCount();
    const heightValue = linesCount * heightExtraSpace;
    setHeight(heightValue <= 600 ? heightValue : 400);
    if (value !== undefined && onChange) {
      onChange(value, linesCount);
    }
  };

  return (
    <div className="flex flex-col gap-sm">
      {/* top bar of code editor */}
      <div className="flex gap-sm md:gap-md">
        {isEditable && (
          <ComboboxComponent
            selectedValue={selectedLanguage.value}
            selectLabel="Select languages..."
            searchLabel="Search languages..."
            notFoundLabel="Not found..."
            optionData={optionsProgrammingLanguage}
            getSelectedValue={handleLanguageSelect}
          />
        )}
        {isEditable && (
          <ComboboxComponent
            selectedValue={selectedTheme.value}
            selectLabel="Select theme..."
            searchLabel="Search theme..."
            notFoundLabel="Not found..."
            optionData={[
              ...Object.entries(monacoThemes).map(([themeId, themeName]) => ({
                label: themeName,
                value: themeId,
              })),
              { label: "VS Dark", value: "vs-dark" },
              { label: "VS Light", value: "light" },
            ]}
            getSelectedValue={handleThemeChange}
          />
        )}
        {!isEditable && (
          <Badge
            className="py-1 bg-secondary dark:bg-secondary-foreground dark:text-white"
            variant={"outline"}
          >
            {selectedLanguage?.label}
          </Badge>
        )}
      </div>
      <div
        className={`relative group border border-3 border-primary border-opacity-50 ${
          !isEditable && "pointer-events-none md:pointer-events-auto"
        }`}
      >
        <MonacoEditor
          value={codeDataProp?.codeValue}
          onMount={handleEditorDidMount}
          onChange={handleEditorChange}
          theme={selectedTheme.value}
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
