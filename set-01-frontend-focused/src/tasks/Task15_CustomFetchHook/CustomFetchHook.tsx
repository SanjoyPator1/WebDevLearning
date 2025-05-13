import useFetch from "./usefetch";

type PostType = {
  userId: number;
  id: number;
  title: string;
  body: string;
}

type PostListType = PostType[]

const POST_URL = "https://jsonplaceholder.typicode.com/posts"

function CustomUseFetchHook() {

  const { data, loading, success, error } = useFetch<PostListType>({
    url: POST_URL,
    timeout: 300
  })


  return (
    <div className="task-container">
      <h2>Task 15: Custom useFetch Hook</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a reusable `useFetch` hook for API calls</li>
          <li>Handle loading, error, and success states</li>
          <li>Accept a timeout parameter to control delay</li>
        </ul>
      </div>

      <div className="implementation space-y-4">
        <div className="flex gap-3">
          <h4>Posts </h4>
          <p>Success Status: {success ? "Succesfully fetched" : "No Success"}</p>
        </div>
        <div className="space-y-3 md:h-[400px] overflow-y-scroll">
          {
            loading ? <p>Loading</p> :
              error ? <p>{error}</p> :
                data && Array.isArray(data) && data.length > 0 &&
                data.map((post) => {
                  return <div key={post.id} className="border rounded-md p-3">
                    <p>
                      {post.title}
                    </p>
                    <p className="font-sm text-gray-600">
                      {
                        post.body
                      }
                    </p>
                    <p className="font-xs text-gray-700">By : {post.userId}</p>
                  </div>
                })

          }
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li><strong>Reusable `useFetch` Hook:</strong> This hook is designed to manage API calls in a centralized and reusable way. It allows components to fetch data from any API with just a `url` and an optional `timeout` parameter. This helps in avoiding the repetition of fetching logic across components.</li>
          <li><strong>State Management:</strong> The hook manages three states - `loading`, `error`, and `success`. It sets `loading` to true initially while waiting for the fetch request to complete. Upon completion, it updates the state with either `data` (if the request is successful) or an `error` message if the request fails. This provides a seamless experience for handling the fetch lifecycle in the component.</li>
          <li><strong>Timeout Simulation:</strong> The hook includes a `timeout` parameter that simulates a network delay before initiating the fetch request. This is useful for simulating slow network conditions or testing how the UI behaves when there is a delay in the response.</li>
          <li><strong>Error Handling:</strong> The hook handles errors gracefully. If the fetch request fails or is aborted, the `error` state is populated with the error message. It also handles `AbortError` gracefully to show that the request was cancelled.</li>
          <li><strong>Abort Controller:</strong> An `AbortController` is used to cancel the fetch request if the component unmounts or if the `useEffect` hook is cleaned up. This prevents state updates on an unmounted component and avoids unnecessary network calls.</li>
          <li><strong>Success Status:</strong> A `success` flag is used to indicate whether the fetch request was successful or not. It allows for easy display of whether data was successfully fetched and handled by the component.</li>
          <li><strong>Loading and Error States:</strong> The component rendering the hook shows a "Loading..." message while data is being fetched and an error message when the fetch fails. This enhances user experience by providing immediate feedback on the request status.</li>
          <li><strong>Key Handling for Data Mapping:</strong> When rendering the list of posts, the `key` prop is assigned to each `div` element based on the unique `id` of the post. This improves React’s ability to efficiently update and manage the DOM, especially when the list changes.</li>
        </ul>
      </div>

    </div>
  );
}

export default CustomUseFetchHook;