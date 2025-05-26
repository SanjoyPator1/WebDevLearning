import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

const dummyImageData = [
  {
    id: 1,
    url: "https://picsum.photos/200/300?random=1"
  },
  {
    id: 2,
    url: "https://picsum.photos/200/300?random=2"
  },
  {
    id: 3,
    url: "https://picsum.photos/200/300?random=3"
  },
  {
    id: 4,
    url: "https://picsum.photos/200/300?random=4"
  },
  {
    id: 5,
    url: "https://picsum.photos/200/300?random=5"
  },
  {
    id: 6,
    url: "https://picsum.photos/200/300?random=6"
  },
]

type mode = "prev" | "next"

function CarouselSlider() {

  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)

  const handleSlidePhoto = (mode: mode) => {
    if (mode === "next") {
      setCurrentPhotoIndex((prev) => (prev + 1) % dummyImageData.length)
    } else {
      setCurrentPhotoIndex((prev) => (prev - 1 + dummyImageData.length) % dummyImageData.length)
    }
  }

  // auto slide images
  useEffect(() => {
    if (isPaused) return

    const intervalId = setInterval(() => {
      setCurrentPhotoIndex((prev) => (prev + 1) % dummyImageData.length)
    }, 2000)

    return () => {
      clearInterval(intervalId)
    }

  }, [isPaused])

  return (
    <div className="task-container">
      <h2>Task 28: Carousel Slider</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a carousel slider component</li>
          <li>Include navigation buttons (next/previous)</li>
          <li>Support auto-slide functionality</li>
        </ul>
      </div>

      <div className="implementation w-full flex flex-col justify-center items-center">
        {/* carousel container */}
        <div
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
          className="relative max-w-md border rounded-md p-6"
        >
          <img
            src={dummyImageData[currentPhotoIndex].url}
            alt={`Slide index-${currentPhotoIndex + 1}`}
            className="w-full transition-all duration-500 ease-in-out"
          />
          <div
            className="flex justify-center gap-2 mt-4"
          >
            {
              dummyImageData.map((_, index) => {
                return (
                  <div className={`h-2 w-2 rounded-full ${index === currentPhotoIndex ? "bg-black" : "bg-gray-400"}`} />
                )
              })
            }
          </div>
          {/* carousel controller */}
          <button
            onClick={() => handleSlidePhoto("prev")}
            // disabled={currentPhotoIndex === 0}
            className="btn btn-primary absolute top-1/2 left-0"
          >
            <ArrowLeft />
          </button>
          <button
            onClick={() => handleSlidePhoto("next")}
            // disabled={currentPhotoIndex === dummyImageData.length-1}
            className="btn btn-primary absolute top-1/2 right-0"
          >
            <ArrowRight />
          </button>
        </div>
        <div className="mt-8">
          <p>
            Current image index : {currentPhotoIndex}
          </p>
          <p>
            Total images : {dummyImageData.length}
          </p>
          <p>
            isPaused : {isPaused.toString()}
          </p>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Used <code>useState</code> to manage the current slide index and pause state of the carousel.</li>
          <li>Implemented circular slide logic using modulo arithmetic to wrap the index for both "next" and "prev" transitions:
            <ul className="list-disc ml-6">
              <li><code>(prev + 1) % length</code> for next</li>
              <li><code>(prev - 1 + length) % length</code> for previous</li>
            </ul>
          </li>
          <li>Enabled auto-slide using <code>useEffect</code> and <code>setInterval</code>, with proper cleanup to avoid memory leaks.</li>
          <li>Auto-slide pauses when the user hovers over the image area by toggling the <code>isPaused</code> state using <code>onMouseEnter</code> and <code>onMouseLeave</code>.</li>
          <li>Included manual slide controls using left/right buttons.</li>
          <li>Added smooth transition animations with Tailwind classes and basic indicators to show the active slide.</li>
        </ul>
      </div>
    </div>
  );
}

export default CarouselSlider;
