# Meeting Transcribe and AI Assistant

This is a Python application that utilizes Amazon Transcribe to perform real-time speech-to-text transcription from a microphone and speaker, capturing both sides of a conversation. The transcribed text is saved to a file, and an optional summary can be generated using Amazon Bedrock.

# Features

- Real-time speech-to-text transcription from microphone and speaker
- Captures both sides of a conversation based on the channel (microphone and speaker) and saves to a stereo audio file
- Supports custom vocabulary for transcription
- Generates summaries using LLM (Large Language Model) hosted in Amazon Bedrock
- Saves transcribed text to a file
- Multi-language support
- Real-time AI assistance for meeting support (Planned)

## Environment

- Python 3.7 or later
- Clone the repository and install the required Python packages using the provided *requirements.txt* file:
```
pip install -r requirements.txt
```
- AWS account and credentials configured ([AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html))

- Tested only on Windows. Does not work on Apple Silicon Macs. The issue is related to sound drivers. Other operating systems are untested.

## Setup

1. Set up AWS credentials. You can follow the instructions in the [AWS SDK for Python (Boto3) Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration) to configure your AWS credentials. Create an IAM User in Your AWS Account and attach the `AmazonTranscribeFullAccess` and `AmazonBedrockFullAccess` policies.

2. (Optional) If you want to use a custom vocabulary with Transcribe, create a custom vocabulary and note its name. Follow the instructions in the [AWS Transcribe Documentation](https://docs.aws.amazon.com/transcribe/latest/dg/custom-vocabulary.html).

3. (Optional) If you want to generate summaries using an LLM, follow the instructions in the [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) for initial setup.

4. Configure the `settings.ini` file with the appropriate values:
   - `language_code`: The language code for transcription (e.g., `en-US` for English, `ja-JP` for Japanese). [Supported Languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
   - `transcribe_region`: The AWS region where you want to use Transcribe. [Supported Regions (see streaming endpoints table)](https://docs.aws.amazon.com/general/latest/gr/transcribe.html)
   - `file_path`: The directory where transcription files will be saved.
   - `save_audio_enabled`: Set to `true` if you want to save the recorded audio file.
   - `custom_vocabulary_enabled`: Set to `true` if you want to use a custom vocabulary.
   - `vocabulary_name`: The name of your custom vocabulary (if `custom_vocabulary_enabled` is `true`).
   - `make_summary_enabled`: Set to `true` if you want to generate summaries using an LLM.
   - `bedrock_region`: The AWS region where you want to configure model access for Bedrock (if `make_summary_enabled` is `true`). [Model support by AWS Region](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)
   - `llm_model_name`: The name of the LLM model to use for summary generation (if `make_summary_enabled` is `true`). You can find the available models in the [Amazon Bedrock model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html).

## Usage

1. Run the `main.py` script.
2. Click the "Start" button to begin transcription.
3. Speak into the microphone, and the transcribed text will appear in the text box.
4. Click the "Stop" button to stop transcription.
5. If `make_summary_enabled` is `true`, a summary file will be generated with the same name as the transcription file, but with a `_summary.txt` extension.

## Notes

- The application records audio from both the microphone (left channel) and the speaker (right channel) to capture both sides of a conversation in a stereo audio file.
- The transcribed text is color-coded based on the channel (microphone or speaker).
- The application supports real-time transcription and saves the transcribed text to a file as it progresses.
- If `make_summary_enabled` is `true`, the summary generation process may take some time depending on the length of the transcription and the LLM model used.


## Disclaimer
This software is provided "as is" without warranty of any kind.
