import { useState, useEffect, FC } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/libs/utils";

interface ComboboxComponentProp {
  initialValue: string;
  selectLabel: string;
  searchLabel: string;
  notFoundLabel: string;
  optionData: {
    label: string;
    value: string;
  }[];
  getSelectedValue: (selectedOption: { label: string; value: string }) => void;
}

const ComboboxComponent: FC<ComboboxComponentProp> = ({
  initialValue,
  selectLabel,
  searchLabel,
  notFoundLabel,
  optionData,
  getSelectedValue,
}) => {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(initialValue);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[200px] justify-between"
        >
          {value
            ? optionData.find((framework) => framework.value === value)?.label
            : selectLabel}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command>
          <CommandInput placeholder={searchLabel} />
          <CommandEmpty>{notFoundLabel}</CommandEmpty>
          <CommandGroup className="h-[40vh] overflow-y-scroll">
            {optionData.map((framework) => (
              <CommandItem
                key={framework.value}
                onSelect={(currentValue) => {
                  setValue(currentValue === value ? "" : currentValue);
                  getSelectedValue(framework);
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    value === framework.value ? "opacity-100" : "opacity-0"
                  )}
                />
                {framework.label}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
};

export default ComboboxComponent;
