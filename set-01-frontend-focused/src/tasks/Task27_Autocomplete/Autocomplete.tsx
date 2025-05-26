import { Check } from "lucide-react";
import { useState } from "react";

const mockSuggestions = [
  "Apple",
  "Banana",
  "Cherry",
  "Date",
  "Grape",
  "Lemon",
  "Mango",
  "Orange",
  "Peach",
  "Pineapple",
  "Strawberry",
  "Watermelon",
];

function AutoCompleteSearch() {
  const [input, setInput] = useState("")
  const [filteredSuggestion, setFilteredSuggestion] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const handleUpdateInput = (newValue: string) => {

    setShowSuggestions(true)
    setInput(newValue)

    const newFilteredSuggestions = mockSuggestions.filter((item) => item.toLowerCase().includes(newValue.toLowerCase()))
    setFilteredSuggestion(newFilteredSuggestions)

  }

  const handleSelectSuggestion = (newValue: string) => {
    setShowSuggestions(false)
    setInput(newValue)
  }

  return (
    <div className="task-container">
      <h2>Task 27: AutoComplete Search</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create an autocomplete search input</li>
          <li>Display suggestions as the user types</li>
          <li>Allow selecting a suggestion to populate the input</li>
        </ul>
      </div>

      <div className="implementation w-[500px] space-y-4">
        <input
          placeholder="type your favourite fruit name"
          value={input}
          onChange={(e) => handleUpdateInput(e.target.value)}
          onBlur={() => {
            setTimeout(()=>{
              setShowSuggestions(false)
            },500)
          }}
          className="w-full"
        />
        {
          showSuggestions &&
          <ul role="listbox" className="border rounded-md p-3 flex flex-col w-full gap-3 md:h-[300px] overflow-y-auto">
            {
              filteredSuggestion.map((item) => {
                return (
                  <li key={item} role="option" aria-selected={input.toLowerCase() === item.toLowerCase()}>
                    <button
                      className="btn btn-secondary flex gap-2 w-full text-left"
                      onClick={() => handleSelectSuggestion(item)}
                    >
                      {
                        input.toLowerCase() === item.toLowerCase() &&
                        <Check />
                      }
                      <span className="flex-1">
                        {item}
                      </span>
                    </button>
                  </li>
                )
              })
            }
          </ul>
        }
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use mock data for suggestions</li>
          <li>Filter suggestions based on user input</li>
        </ul>
      </div>
    </div>
  );
}

export default AutoCompleteSearch;
