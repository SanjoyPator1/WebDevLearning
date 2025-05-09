function CarouselSlider() {
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

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useState` to track the active slide</li>
          <li>Use `setInterval` for auto-slide functionality</li>
        </ul>
      </div>
    </div>
  );
}

export default CarouselSlider;
