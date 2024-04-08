"""
    This Python script uses the AWS Bedrock runtime service to generate a summary of a given text file using an AI language model.
    It reads the content of the provided file and a system prompt file (system_prompt.txt), which contains instructions for the model.
    If the system prompt file is not found, it uses a default prompt. The script then sends a request to the Bedrock runtime service with the file content and system prompt, and receives a response containing the generated summary text.
    The summary is then written to a new file with the same name as the input file but with a '_summary.txt' extension.
"""
import boto3
import json
from botocore.exceptions import BotoCoreError, ClientError

def make_summary(file_path, model_name, region):
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"The specified file was not found: {file_path}")
        return

    try:
        with open('system_prompt.txt', 'r', encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        try:
            message = "The system_prompt.txt file was not found. write here the system prompt you want to use."
            with open('system_prompt.txt', 'w', encoding="utf-8") as f:
                f.write(message)
            return
        except IOError as e:
            print(f"An error occurred while writing to the summary file: {e}")
            return

    try:
        # Initialize the Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": file_content
                    }
                ]
            }
        )
        modelId = model_name
        accept = 'application/json'
        contentType = 'application/json'
        response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
        response_body = json.loads(response.get('body').read())
        answer = response_body["content"][0]["text"]
    except (BotoCoreError, ClientError) as error:
        print(f"An error occurred while calling AWS service: {error}")
        return
    except KeyError:
        print("Could not retrieve required data from the response.")
        return

    try:
        with open(file_path + '_summary.txt', 'w', encoding="utf-8") as f:
            f.write(answer)
    except IOError as e:
        print(f"An error occurred while writing to the summary file: {e}")
    

# Execute the following code only if this file is run directly
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        model_name = sys.argv[2]
        region = sys.argv[3]
    else:
        print("Usage: python make_summary.py <file_path> <model_name> <region>")
        sys.exit(1)
    make_summary(file_path, model_name, region)
