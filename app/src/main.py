import os
import json
import uuid
import tempfile
from flask import Flask, render_template, request, jsonify, send_from_directory
from google.cloud import texttospeech
from google import genai
from google.genai.types import HttpOptions, ModelContent, Part, UserContent
from moviepy.editor import AudioFileClip, concatenate_audioclips

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/audio'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

GCP_PROJECT_ID = os.environ['GOOGLE_CLOUD_PROJECT']
GCP_LOCATION   = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')

if not GCP_PROJECT_ID or GCP_PROJECT_ID == 'your-gcp-project-id':
    print("WARNING: GOOGLE_CLOUD_PROJECT environment variable not set or is default. Please set it.")
    print("Alternatively, replace 'your-gcp-project-id' in app.py with your actual GCP Project ID.")

try:
    gemini_model = genai.Client(http_options=HttpOptions(api_version="v1"))
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    print(f"Error initializing Google Cloud services: {e}")
    print("Please ensure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION environment variables are set correctly and APIs are enabled.")
    gemini_model = None
    tts_client = None

# https://cloud.google.com/text-to-speech/docs/voices
VOICE_MAP = {
    "speaker_1": "en-US-Chirp3-HD-Achernar",  # Female
    "speaker_2": "en-US-Chirp3-HD-Algenib",
    "speaker_3": "en-US-Chirp3-HD-Aoede",     # Female
    "speaker_4": "en-US-Chirp3-HD-Schedar",
}

def generate_transcript_with_gemini(description, num_guests):
    """
    Generates a fictional podcast transcript using Gemini based on description and guest count.
    Returns a list of dictionaries following the specified format.
    """
    if gemini_model is None:
        raise ConnectionError("Google Cloud Vertex AI (Gemini) client not initialized.")

    chat_session = gemini_model.chats.create(
        model="gemini-2.0-flash-001",
    )

    prompt = f"""
    Generate a short, fictional podcast transcript based on the following description: "{description}".
    The podcast should feature exactly {num_guests} distinct speakers.
    Format the output as a JSON array of objects. Each object must have two keys:
    "speaker_id": A string identifier like "speaker_1", "speaker_2", ..., up to "speaker_{num_guests}".
    "speaker_text": The dialogue for that speaker segment.

    ## Important
    * speaker_1 and speaker_3 are female voices, while speaker_2 and speaker_4 are Male voices. 

    Ensure the JSON is valid and contains only the array. Do NOT include any extra text, markdown, or formatting outside the JSON array.
    The transcript should flow naturally with dialogue between the speakers.
    Example structure:
    [
      {{"speaker_id": "speaker_1", "speaker_text": "Hello and welcome!"}},
      {{"speaker_id": "speaker_2", "speaker_text": "Great to be here."}},
      // ... more segments
    ]
    """

    try:
        response = chat_session.send_message(prompt)
        text_response = response.text.strip()
        if text_response.startswith('```json'):
            text_response = text_response[7:]
        if text_response.endswith('```'):
            text_response = text_response[:-3]
        text_response = text_response.strip()


        print("Gemini raw response text:", text_response)

        transcript_data = json.loads(text_response)

        if not isinstance(transcript_data, list):
            raise ValueError("Gemini response is not a JSON list.")
        for item in transcript_data:
            if not isinstance(item, dict) or 'speaker_id' not in item or 'speaker_text' not in item:
                 if not (isinstance(item, dict) and any('speaker' in k.lower() and 'text' in v for k, v in item.items())):
                    raise ValueError("Gemini response items are not in the expected format {speaker_id: ..., speaker_text: ...}.")
        return transcript_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print("Attempting to find JSON in problematic response:")
        print(text_response)
        raise ValueError("Failed to parse transcript from Gemini response. The format was incorrect.") from e
    except Exception as e:
        print(f"Error generating transcript with Gemini: {e}")
        raise ConnectionError(f"Failed to generate transcript with Gemini: {e}")


def synthesize_text_to_speech(text, voice_name):
    """
    Converts text to speech using Google Text-to-Speech. Returns audio content bytes.
    """
    if tts_client is None:
         raise ConnectionError("Google Cloud Text-to-Speech client not initialized.")

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        name=voice_name,
        language_code="en-US",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        print(f"Error synthesizing speech for voice {voice_name}: {e}")
        raise ConnectionError(f"Text-to-Speech failed: {e}")


def stitch_audio_files(audio_file_paths):
    """
    Stitches multiple audio files into one using MoviePy. Returns the path to the combined file.
    """
    if not audio_file_paths:
        return None

    try:
        audio_clips = [AudioFileClip(f) for f in audio_file_paths]
        combined_clip = concatenate_audioclips(audio_clips)

        unique_filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        combined_clip.write_audiofile(output_path)

        for clip in audio_clips:
            clip.close()
        combined_clip.close()

        return unique_filename
    except Exception as e:
        print(f"Error stitching audio files: {e}")
        raise RuntimeError(f"Audio stitching failed: {e}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate_podcast', methods=['POST'])
def generate_podcast():
    data = request.json
    description = data.get('description')
    num_guests = data.get('guests')

    if not description:
        return jsonify({"error": "Podcast description is required."}), 400
    try:
        num_guests = int(num_guests)
        if not 1 <= num_guests <= 4:
             return jsonify({"error": "Number of guests must be between 1 and 4."}), 400
    except ValueError:
         return jsonify({"error": "Invalid number of guests."}), 400

    if gemini_model is None or tts_client is None:
         return jsonify({"error": "Backend services not initialized. Check server logs."}), 500


    temp_files = []

    try:
        transcript = generate_transcript_with_gemini(description, num_guests)
        print("Generated Transcript:", transcript)

        audio_segment_files = []
        speaker_voices = {}

        for segment in transcript:
            speaker_id = segment.get("speaker_id")
            text = segment.get("speaker_text")

            if not speaker_id or not text:
                 print(f"Skipping invalid segment: {segment}")
                 continue

            if speaker_id not in speaker_voices:
                if len(speaker_voices) < num_guests and speaker_id in VOICE_MAP:
                     speaker_voices[speaker_id] = VOICE_MAP[speaker_id]
                     print(f"Assigned voice {VOICE_MAP[speaker_id]} to {speaker_id}")
                else:
                     fallback_voice = "en-US-Standard-A"
                     speaker_voices[speaker_id] = fallback_voice
                     print(f"WARNING: No specific voice found for {speaker_id} or more speakers than defined voices. Using fallback voice {fallback_voice}.")

            voice_name = speaker_voices.get(speaker_id)
            if not voice_name:
                 print(f"Could not determine voice for {speaker_id}. Skipping segment.")
                 continue

            print(f"Synthesizing for {speaker_id} ({voice_name}): '{text[:50]}...'")

            audio_content = synthesize_text_to_speech(text, voice_name)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp:
                fp.write(audio_content)
                temp_files.append(fp.name)
                audio_segment_files.append(fp.name)

        if not audio_segment_files:
             return jsonify({"error": "No audio segments were successfully generated."}), 500

        print("Stitching audio files:", audio_segment_files)
        final_audio_filename = stitch_audio_files(audio_segment_files)

        if not final_audio_filename:
             return jsonify({"error": "Failed to stitch audio segments."}), 500

        audio_url = f'/static/audio/{final_audio_filename}'
        return jsonify({"audio_url": audio_url})

    except ValueError as e:
        print(f"Processing error: {e}")
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
         print(f"Google Cloud API error: {e}")
         return jsonify({"error": f"Google Cloud service failed: {e}. Check API keys/permissions and server logs."}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500
    finally:
        for f_path in temp_files:
            try:
                os.remove(f_path)
                print(f"Cleaned up temporary file: {f_path}")
            except OSError as e:
                print(f"Error removing temporary file {f_path}: {e}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

