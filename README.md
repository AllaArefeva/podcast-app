# AI Podcast Generator

This project is a web-based application that uses generative AI to create short, fictional podcasts from a user-provided description. The application leverages Google's Gemini Pro for transcript generation and Google's Text-to-Speech API for audio synthesis.

## Features

- **Generates unique podcast transcripts** based on user descriptions using Gemini.
- **Synthesizes transcripts into high-quality audio** with distinct voices for each speaker using Google Text-to-Speech.
- **Stitches audio segments together** to create a complete podcast episode.
- **Simple and intuitive web interface** for generating and listening to podcasts.
- **Easy deployment** to Google Cloud Run.

## Architecture

The application consists of a single Flask backend that serves a static HTML/JavaScript frontend.

1.  **User Interface (index.html)**: The user enters a description for the podcast and selects the number of speakers.
2.  **Flask Backend (main.py)**:
    *   Receives the user's request.
    *   Calls the Gemini API to generate a podcast transcript in JSON format.
    *   For each line in the transcript:
        *   Calls the Google Text-to-Speech API to generate an audio segment for the corresponding speaker.
    *   Stitches all the audio segments together into a single audio file using `moviepy`.
    *   Returns the URL of the generated audio file to the user interface.
3.  **User Interface (index.html)**: The generated podcast is played back to the user in an HTML audio player.

## Getting Started

### Prerequisites

*   Python 3.7+
*   Google Cloud SDK
*   A Google Cloud Project with the following APIs enabled:
    *   Vertex AI API
    *   Text-to-Speech API

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/podcast-app.git
    cd podcast-app
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r app/src/requirements.txt
    ```

4.  **Set up your environment variables:**

    ```bash
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="your-gcp-region"
    ```

### Running the Application Locally

1.  **Run the Flask application:**

    ```bash
    python app/src/main.py
    ```

2.  Open your browser and navigate to `http://localhost:8080`.

## Deployment

The application can be easily deployed to Google Cloud Run using the provided `deploy.sh` script.

1.  **Make sure you are authenticated with the Google Cloud SDK:**

    ```bash
    gcloud auth login
    gcloud config set project your-gcp-project-id
    ```

2.  **Run the deployment script:**

    ```bash
    bash app/deploy.sh
    ```

This will deploy the application to Google Cloud Run and make it accessible at a public URL.

## Usage

1.  Enter a description of the podcast you want to generate in the "Podcast Topic/Description" text area.
2.  Select the number of speakers you want in the podcast.
3.  Click the "Generate Podcast" button.
4.  The application will generate the podcast and a player will appear, allowing you to listen to the generated audio.

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.