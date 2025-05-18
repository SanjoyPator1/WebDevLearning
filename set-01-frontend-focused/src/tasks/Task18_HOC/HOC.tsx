import UserCard, { type UserType } from "./UserCard";
import { withLoading } from "./WithLoaderHOC";

const UserProfileWithLoading = withLoading(UserCard);

const dummyUserData: UserType = {
  name: "Jane Doe",
  email: "jane.doe@example.com",
};

function HigherOrderComponents() {
  return (
    <div className="task-container">
      <h2>Task 18: Higher Order Components</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a `withLoading` HOC</li>
          <li>Wrapped components should show a spinner while loading</li>
          <li>Pass the loading state into the wrapped component</li>
        </ul>
      </div>

      <div className="implementation">
        <UserProfileWithLoading userData={dummyUserData} />
      </div>

      <div className="task-notes bg-gray-50 p-6 rounded-lg border border-gray-200 mt-8">
        <h3 className="text-xl font-semibold text-gray-800 mb-4">
          Implementation Notes:
        </h3>
        <ul className="space-y-4 text-gray-700">
          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">HOC Pattern Principles:</p>
              <p className="mt-1">
                Higher Order Components follow the principle of composition
                rather than inheritance. The pattern involves creating a
                function that takes a component as an argument and returns a new
                enhanced component. This aligns with React's compositional
                nature, allowing us to reuse component logic across multiple
                components without modifying their implementation.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">Props Handling:</p>
              <p className="mt-1">
                The HOC pattern requires careful props management to ensure the
                wrapped component receives all its expected props. We use the
                spread operator (
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  {`...props`}
                </code>
                ) to forward all received props to the wrapped component, along
                with any additional props the HOC adds (like{" "}
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  isLoading
                </code>
                ). This maintains the wrapped component's API while enhancing it
                with new functionality.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">TypeScript Integration:</p>
              <p className="mt-1">
                When implementing HOCs with TypeScript, we use generics to
                ensure type safety across components. The pattern{" "}
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  &lt;P extends object&gt;
                </code>{" "}
                allows our HOC to work with any component props while preserving
                their types. Additionally, we use intersection types (
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  P & WithLoadingProps
                </code>
                ) to combine original props with our injected props.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">State Encapsulation:</p>
              <p className="mt-1">
                The HOC pattern excels at encapsulating cross-cutting concerns
                like loading states. By managing the loading logic in the HOC,
                we keep component implementations clean and focused on their
                primary responsibilities. This separation improves
                maintainability and reduces code duplication across the
                application.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">Display Name Configuration:</p>
              <p className="mt-1">
                Setting{" "}
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  displayName
                </code>{" "}
                on the generated component is important for debugging purposes.
                Without this, React DevTools would display generic component
                names, making it difficult to identify wrapped components in the
                component tree. The format{" "}
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  withLoading(ComponentName)
                </code>{" "}
                clearly indicates both the HOC and the wrapped component.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">Composition vs Inheritance:</p>
              <p className="mt-1">
                HOCs exemplify React's preference for composition over
                inheritance. Rather than creating complex class hierarchies,
                HOCs compose behavior by wrapping components. This approach
                provides greater flexibility and allows for combining multiple
                HOCs to add different features to components (
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  withAuth(withLoading(Component))
                </code>
                ).
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="inline-block w-5 h-5 bg-blue-500 rounded-full flex-shrink-0 mt-1 mr-3"></span>
            <div>
              <p className="font-medium">React Hooks Alternative:</p>
              <p className="mt-1">
                While modern React tends to favor hooks like{" "}
                <code className="px-1 py-0.5 bg-gray-100 rounded text-sm">
                  useLoading()
                </code>{" "}
                for reusable logic, HOCs remain useful in certain scenarios.
                They're particularly valuable when you need to completely
                control the rendering of components based on shared conditions,
                rather than just sharing logic.
              </p>
            </div>
          </li>
        </ul>

        <div className="bg-blue-50 border border-blue-200 rounded p-4 mt-6">
          <h4 className="font-semibold text-blue-800 mb-2">Best Practices:</h4>
          <ul className="space-y-1 text-blue-700">
            <li>
              • Don't mutate the original component; always create a new one
            </li>
            <li>• Use meaningful display names for debugging</li>
            <li>• Pass unrelated props through to the wrapped component</li>
            <li>
              • Avoid using HOCs inside the render method to prevent unnecessary
              remounting
            </li>
            <li>
              • Consider composability when designing HOCs to work well with
              other HOCs
            </li>
            <li>
              • Use the "spread and rest" pattern to handle unknown props
              effectively
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default HigherOrderComponents;
