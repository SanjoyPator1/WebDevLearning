import { ArrowDown, ArrowUp, Check } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

// type for our context
type SelectContextType = {
  isOpen: boolean;
  selectedValue: string | null;
  toggleDropdown: () => void;
  closeDropdown: () => void;
  handleSelect: (value: string) => void;
};

// create context
const SelectContext = createContext<SelectContextType | undefined>(undefined);

// hook to use the select context
const useSelectContext = () => {
  const context = useContext(SelectContext);

  if (!context) {
    throw new Error(
      "Select compound components must be used within a Select component"
    );
  }

  return context;
};

type SelectProps = {
  value: string | null;
  onChange: (value: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
};

type OptionProps = {
  value: string;
  children: React.ReactNode;
  className?: string;
};

type TriggerProps = {
  children: React.ReactNode;
  className?: string;
};

type DropdownProps = {
  children: React.ReactNode;
  className?: string;
};

// main select component
const Select = ({
  children,
  onChange,
  value,
  className,
  disabled,
}: SelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement>(null);

  const toggleDropdown = useCallback(() => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled]);

  const closeDropdown = useCallback(() => setIsOpen(false), []);

  const handleSelect = useCallback(
    (optionValue: string) => {
      onChange(optionValue);
      closeDropdown();
    },
    [onChange, closeDropdown]
  );

  // handle outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isOpen) {
        if (
          selectRef.current &&
          !selectRef.current.contains(event.target as Node)
        ) {
          closeDropdown();
        }
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    // cleanup event listener
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const contextValue: SelectContextType = {
    isOpen,
    toggleDropdown,
    closeDropdown,
    handleSelect,
    selectedValue: value,
  };

  return (
    <SelectContext.Provider value={contextValue}>
      <div
        ref={selectRef}
        className={`
                relative w-full ${
                  disabled ? "opacity-60 cursor-not-allowed" : ""
                } ${className}
                `}
      >
        {children}
      </div>
    </SelectContext.Provider>
  );
};

// trigger button
const Trigger = ({ children, className }: TriggerProps) => {
  const { toggleDropdown, isOpen } = useSelectContext();

  return (
    <button
      onClick={toggleDropdown}
      className={`
            w-full flex items-center justify-between border border-gray-300 btn
            ${isOpen ? "ring-2 ring-blue-500 border-blue-500" : ""}
             ${className}
            `}
      aria-haspopup="listbox"
      aria-expanded={isOpen}
    >
      {children}
      {isOpen ? <ArrowUp /> : <ArrowDown />}
    </button>
  );
};

// dropdown component
const Dropdown = ({ children, className }: DropdownProps) => {
  const { isOpen } = useSelectContext();

  if (!isOpen) return null;

  return (
    <div
      className={`absolute w-full z-10 mt-1 max-h-60 overflow-y-auto bg-white shadow-lg rounded-md  ${className}`}
      role="listbox"
    >
      <ul className="py-1 p-0!">{children}</ul>
    </div>
  );
};

// options component
const Option = ({ children, value, className }: OptionProps) => {
  const { handleSelect, selectedValue } = useSelectContext();
  const isSelected = selectedValue === value;

  return (
    <li
      onClick={() => handleSelect(value)}
      className={`flex items-center justify-between cursor-pointer py-2 px-4 text-sm ${
        isSelected
          ? "bg-blue-100 text-blue-900 font-medium"
          : "text-gray-900 hover:bg-gray-100"
      } ${className}`}
      role="option"
      aria-selected={isSelected}
    >
      <div className="flex items-center">
        <span
          className={`block truncate ${
            isSelected ? "font-medium" : "font-normal"
          }`}
        >
          {children}
        </span>
      </div>
      {isSelected && (
        <span>
          <Check className="w-5 h-5" />
        </span>
      )}
    </li>
  );
};

Select.Trigger = Trigger;
Select.Dropdown = Dropdown;
Select.Option = Option;

export default Select;
