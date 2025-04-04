# ShowTrackr

A Vue.js application for tracking TV shows and managing your watchlist.

## Overview

ShowTrackr helps you keep track of your favorite TV shows. You can discover new shows, mark episodes as watched, maintain a watchlist, and see statistics about your viewing habits.

![ShowTrackr Screenshot](src/assets/images/screenshot.png)

## Features

- 📺 Browse popular TV shows
- 🔍 Search for shows by title, genre, or actor
- ✓ Track episodes you've watched
- 📊 View statistics about your watching habits
- 📝 Create and manage your personal watchlist
- 📱 Responsive design for desktop and mobile

## Tech Stack

- Vue.js 3 (Composition API)
- TypeScript
- Pinia for state management
- Vue Router
- Tailwind CSS
- Vite
- TVMaze API

## Getting Started

### Prerequisites

- Node.js (v16+)
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/showtrackr.git
cd showtrackr
```

2. Install dependencies:
```bash
npm install
# or
yarn
```

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open your browser and visit `http://localhost:5173`

## Project Structure

```
showtrackr/
├── public/              # Static assets
├── src/
│   ├── assets/          # Images, styles, etc.
│   ├── components/      # Vue components
│   ├── composables/     # Reusable composition functions
│   ├── layouts/         # Page layouts
│   ├── models/          # TypeScript interfaces
│   ├── router/          # Vue Router configuration
│   ├── services/        # API services
│   ├── stores/          # Pinia stores
│   ├── utils/           # Utility functions
│   ├── views/           # Page components
│   ├── App.vue          # Root component
│   └── main.ts          # Application entry point
└── ...                  # Configuration files
```

## Learning Resources

This project follows a structured learning path for Vue.js. Check out the [ROADMAP.md](ROADMAP.md) file for a step-by-step guide to building this application while learning Vue.js concepts.

## API Integration

This project uses the [TVMaze API](https://www.tvmaze.com/api) to fetch TV show data. No API key is required for basic usage.

## License

MIT

## Acknowledgments

- [TVMaze](https://www.tvmaze.com/) for providing the API
- [Vue.js](https://vuejs.org/) for the amazing framework
- [Tailwind CSS](https://tailwindcss.com/) for the utility-first CSS framework