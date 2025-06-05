import { useEffect, useRef, useState } from "react";

const MOCK_DATA: string[] = [
  'Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5',
  'Item 6', 'Item 7', 'Item 8', 'Item 9', 'Item 10',
  'Item 11', 'Item 12', 'Item 13', 'Item 14', 'Item 15',
  'Item 16', 'Item 17', 'Item 18', 'Item 19', 'Item 20'
];

const LIMIT = 3

function InfiniteScroll() {
  const [visibleList, setVisibleList] = useState<string[]>(MOCK_DATA.slice(0, LIMIT))
  const [isLoading, setIsLoading] = useState(false)
  const observerRef = useRef<HTMLDivElement>(null)

  // function to load more data and update the visible list state
  const handleLoadMore = () => {
    console.log("handle load more function called")

    setIsLoading(true)
    setTimeout(() => {
      setVisibleList((prev) => {
        // set the new visible list
        const newList = MOCK_DATA.slice(visibleList.length, visibleList.length + LIMIT)
        return [...prev, ...newList]
      })
      // set loading false
      setIsLoading(false)
    }, 500)
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isLoading && visibleList.length < MOCK_DATA.length) {
          handleLoadMore()
        }
      },
      {
        threshold: 0.5
      }
    )

    const current = observerRef.current
    if (current) {
      observer.observe(current)
    }

    return () => {
      if (current) {
        observer.unobserve(current)
      }
    }

  }, [isLoading, visibleList])

  return (
    <div className="task-container">
      <h2>Task 30: Infinite Scroll</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Implement infinite scrolling for a list</li>
          <li>Load more items as the user scrolls down</li>
        </ul>
      </div>

      <div className="implementation max-h-[200px] overflow-y-auto rounded-md border bg-gray-50">
        {/* display the list */}
        <ul className="space-y-4">
          {
            visibleList.map((item) => {
              return (
                <div
                  key={item}
                  className="bg-white rounded-md p-2 shadow-sm"
                >
                  {item}
                </div>
              )
            })
          }
        </ul>

        {/* div ref for observer */}
        <div ref={observerRef} className="h-10" />

        {/* loading container */}
        {
          isLoading && (
            <div className="py-2 animate-pulse text-blue-500 text-center">
              Loading...
            </div>
          )
        }

        {/* show when the complete data list is shown */}
        {
          visibleList.length === MOCK_DATA.length && (
            <div className="py-2 text-green-500 text-center">
              All data loaded
            </div>
          )
        }

      </div>

      <div className="task-notes mt-6">
        <h3 className="text-lg font-semibold mb-2">Implementation Notes:</h3>
        <ul className="text-gray-700 space-y-2">
          <li>
            This infinite scroll feature is implemented using the{' '}
            <code className="bg-gray-200 px-1 rounded text-sm">IntersectionObserver</code> API instead of traditional scroll event listeners.
          </li>
          <li>
            A hidden <code className="bg-gray-200 px-1 rounded text-sm">&lt;div&gt;</code> is placed at the bottom of the scrollable list and referenced using{' '}
            <code className="bg-gray-200 px-1 rounded text-sm">useRef()</code>. This serves as the <strong>sentinel element</strong>.
          </li>
          <li>
            The observer is initialized in a <code className="bg-gray-200 px-1 rounded text-sm">useEffect</code> hook. It monitors when the sentinel enters the viewport using a
            <code className="bg-gray-200 px-1 rounded text-sm">threshold</code> of <strong>0.5</strong>, meaning the callback runs when 50% of the sentinel is visible.
          </li>
          <li>
            When the observer detects intersection and more data is available, it triggers the <code className="bg-gray-200 px-1 rounded text-sm">handleLoadMore()</code> function,
            which appends the next chunk of items to the current list.
          </li>
          <li>
            The list of items is stored in local component state (<code className="bg-gray-200 px-1 rounded text-sm">visibleList</code>) and grows incrementally until all mock data is loaded.
          </li>
          <li>
            A simulated network delay is added using <code className="bg-gray-200 px-1 rounded text-sm">setTimeout</code> to mimic real API behavior.
          </li>
          <li>
            Once all data is loaded, the sentinel remains but no further loading occurs, and a message <strong>"All data loaded"</strong> is shown.
          </li>
          <li>
            This approach is declarative, efficient, and avoids manual scroll calculations—making it more performant and easier to manage in React.
          </li>
        </ul>
      </div>

    </div>
  );
}

export default InfiniteScroll;
