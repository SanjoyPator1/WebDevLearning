import React from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../ui/command";

interface commandComponentProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  options: {
    label: string;
    value: string;
  }[];
  getSelectedValue: (selectedOption: {
    label: string;
    value: string;
  }) => void;
}

export function SearchSelectCommand({
  open,
  setOpen,
  options,
  getSelectedValue,
}: commandComponentProps) {
  const optionSelectHandler = (selectedOption: {
    label: string;
    value: string;
  }) => {
    setOpen(false);
    console.log({ selectedOption });
    getSelectedValue(selectedOption);
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search Users..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Suggestions">
          {options &&
            options.length > 0 &&
            options.map((option) => (
              <CommandItem key={option.value}>
                <div
                  onClick={() => optionSelectHandler(option)}
                  className="flex flex-row items-center p-base-container gap-md"
                >
                  {option.label.toString()}
                </div>
              </CommandItem>
            ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
