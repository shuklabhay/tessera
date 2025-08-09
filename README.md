# Tessera

[![Pages Deploy](https://github.com/shuklabhay/tessera/actions/workflows/deploy.yml/badge.svg)](https://github.com/shuklabhay/tessera/actions/workflows/deploy.yml)
[![Lint](https://github.com/shuklabhay/tessera/actions/workflows/lint_py.yml/badge.svg)](https://github.com/shuklabhay/tessera/actions/workflows/lint_py.yml)

![banner](https://github.com/shuklabhay/tessera/blob/main/web/assets/banner.jpg?raw=true)

## App Info

Conversational voice agent for auditory rehabilitation through adaptive listening exercises. View more information [here.](https://shuklabhay.github.io/tessera/)

## Features

- Real-time voice interaction with AI assistant powered by Google Gemini
- Immersive 3D audio scenarios with spatial positioning and environmental sounds
- Adaptive difficulty based on user performance and progress tracking
- Audio-based exercises for hearing rehabilitation and auditory training
- Visual feedback through animated orb interface
- Session persistence and progress monitoring

## Setup

- [Install](https://www.python.org/downloads/) Python 3.12.3 or higher
  - Confirm installation by running `python --version` in the command line
- [Install](https://github.com/kivy/kivy#installation) Kivy dependencies for your platform
- Install required packages by running `pip install -r requirements.txt`

## Build app

- Install required packages by running `pip install -r requirements.txt`
- From the root directory run `pyinstaller Tessera.spec`

### API Key Setup

- Get a Google Gemini API key from [Google AI Studio](https://aistudio.google.com/u/1/apikey)
- Create a `.env` file in the project root directory
- Add your API key to the `.env` file:
  ```
  GEMINI_API_KEY=your_api_key_here
  ```
- **Privacy Note**: Your API key is never saved or transmitted anywhere except directly to Google's Gemini API. It remains on your local machine only.

## Development

- Run `python src/main.py` to start the application
- Run `black src/` to format Python code

## Project Structure

- `src/main.py` - Application entry point
- `src/ui/` - Kivy-based user interface components
- `src/managers/` - Core logic and state management
- `src/audio_engine/` - Audio playback and mixing functionality
- `src/services/` - External service integrations (Gemini, TTS, etc.)
- `web/` - Static website files for GitHub Pages deployment
- `audio/` - WAV audio files organized by category

## License

This project is licensed under the MIT License - see the LICENSE file for details.
