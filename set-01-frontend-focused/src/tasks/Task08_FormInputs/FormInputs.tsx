import { useState } from "react";

interface IFormState {
  name: string;
  email: string;
  password: string;
}

const initialFormData: IFormState = {
  name: "",
  email: "",
  password: "",
};

const inputFields = [
  {
    name: "name",
    type: "text",
    label: "Name",
    placeholder: "Enter Name",
  },
  {
    name: "email",
    type: "email",
    label: "Email",
    placeholder: "Enter Email",
  },
  {
    name: "password",
    type: "password",
    label: "Password",
    placeholder: "Enter Password",
  },
];

function FormInputs() {
  const [formData, setFormData] = useState<IFormState>(initialFormData);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(
      `Submitted form:\nName: ${formData.name}\nEmail: ${formData.email}\nPassword: ${formData.password}`
    );
  };

  const handleReset = () => {
    setFormData(initialFormData);
  };

  return (
    <div className="task-container">
      <h2>Task 8: Form with Multiple Inputs</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Name, email, password fields</li>
          <li>Show entered data below form</li>
          <li>Reset button to clear form</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-4 mt-4">
        <form
          onSubmit={handleSubmit}
          onReset={handleReset}
          className="flex flex-col gap-4"
        >
          {inputFields.map((field) => (
            <div key={field.name} className="flex flex-col gap-1">
              <label htmlFor={field.name} className="font-medium">
                {field.label}
              </label>
              <input
                id={field.name}
                name={field.name}
                type={field.type}
                value={formData[field.name as keyof IFormState]}
                onChange={handleChange}
                placeholder={field.placeholder}
                aria-label={field.label}
                aria-required="true"
                required
                className="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}

          <div className="flex gap-2">
            <button type="submit" className="btn btn-primary">
              Submit
            </button>
            <button type="reset" className="btn btn-secondary">
              Reset
            </button>
          </div>
        </form>

        <section className="text-gray-800" aria-live="polite">
          <h4 className="font-semibold mb-1">Entered Data:</h4>
          <ul className="list-disc list-inside">
            <li>
              <strong>Name:</strong> {formData.name}
            </li>
            <li>
              <strong>Email:</strong> {formData.email}
            </li>
            <li>
              <strong>Password:</strong> {formData.password}
            </li>
          </ul>
        </section>
      </div>

      <div className="task-notes mt-6">
        <h3>Implementation Notes:</h3>
        <ul className="list-disc list-inside">
          <li>
            Used a centralized array for input field definitions to reduce
            repetition.
          </li>
          <li>
            Added proper labels with <code>htmlFor</code> and <code>id</code>{" "}
            for accessibility.
          </li>
          <li>
            Used <code>aria-label</code> and <code>aria-required</code> for
            screen reader support.
          </li>
          <li>
            Ensured keyboard accessibility and form semantics using{" "}
            <code>&lt;form&gt;</code>, <code>&lt;label&gt;</code>, and proper
            button types.
          </li>
          <li>
            Used <code>aria-live="polite"</code> to announce entered data
            updates for assistive technologies.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default FormInputs;
