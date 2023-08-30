import React from "react";
import { ChevronDownIcon, ChevronUpIcon, CheckIcon } from "lucide-react";
import classnames from "classnames";
import * as Select from "@radix-ui/react-select";
import { Button } from "./ui/button";

type CustomSelectProps = {
  placeholder: string;
  label: string;
  options: string[];
  onSelect: (selected: string) => void;
  selectedValue: string;
};

const SelectComponent: React.FC<CustomSelectProps> = ({
  placeholder,
  label,
  options,
  onSelect,
}) => {
  return (
    <Select.Root>
      <Select.Trigger className="SelectTrigger">
        <Button>
          <Select.Value placeholder={placeholder} />
          <Select.Icon className="SelectIcon">
            <ChevronDownIcon />
          </Select.Icon>
        </Button>
      </Select.Trigger>
      <Select.Portal className="bg-primary-foreground dark:bg-primary p-base-container border-3">
        <Select.Content className="SelectContent">
          <Select.ScrollUpButton className="SelectScrollButton">
            <ChevronUpIcon />
          </Select.ScrollUpButton>
          <Select.Viewport className="SelectViewport">
            <Select.Group>
              <Select.Label className="SelectLabel">{label}</Select.Label>
              {options.map((option) => (
                <SelectItem value={option} onSelectHandler={onSelect}>
                  {option}
                </SelectItem>
              ))}
            </Select.Group>
          </Select.Viewport>
          <Select.ScrollDownButton className="SelectScrollButton">
            <ChevronDownIcon />
          </Select.ScrollDownButton>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
};

type SelectItemProps = {
  value: string;
  onSelectHandler: (selected: string) => void;
  children?: React.ReactNode;
};

const SelectItem: React.FC<SelectItemProps> = ({
  value,
  onSelectHandler,
  children,
}) => {
  return (
    <Select.Item
      className={classnames("SelectItem flex justify-between gap-2")}
      value={value}
      onSelect={() => {
        console.log({ "selected value": "" + value });
        onSelectHandler(value);
      }}
    >
      <Select.ItemText>{children}</Select.ItemText>
      <Select.ItemIndicator className="SelectItemIndicator">
        <CheckIcon />
      </Select.ItemIndicator>
    </Select.Item>
  );
};

export default SelectComponent;
