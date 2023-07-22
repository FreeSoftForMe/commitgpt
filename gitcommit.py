import argparse
import json
import logging
import os
import re
import subprocess
import requests
import tiktoken
from PyInquirer import prompt

MODEL_NAME = "MODEL_NAME"
OPENAI_API_KEY = "OPENAI_API_KEY"
TASK_PREFIX = "TASK_PREFIX"
OPENAI_API_URL = "OPENAI_API_URL"
MAX_TOKEN_COUNT = "MAX_TOKEN_COUNT"
TEMPERATURE = "TEMPERATURE"
GIT_COMMAND = "GIT_COMMAND"
MESSAGE_TEMPLATE = "MESSAGE_TEMPLATE"
YOUR_TOKEN_KEY = "YOUR_TOKEN_KEY"
YOUR_TASK_PREFIX = "YOUR_TASK_PREFIX"



def parse_args():
    """Parses command-line arguments for the logging level."""
    parser = argparse.ArgumentParser(description='Provide logging level.')
    parser.add_argument('--log', metavar='log', type=str, help='Logging level: debug, info, warning, error, critical')
    return parser.parse_args()


def configure_logging(args):
    """Configures the logging level based on the provided command-line arguments."""
    level = args.log.strip().upper() if args.log else 'CRITICAL'
    logging.basicConfig(level=level, 
                        format='%(asctime)s - %(levelname)s - %(message)s', 
                        datefmt='%d-%b-%y %H:%M:%S')


def load_config():
    """Loads the configuration file and asks the user to input their OpenAI API key if not already provided."""
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(script_dir, "config.json")

        with open(config_path) as config_file:
            config = json.load(config_file)
    
        if config[OPENAI_API_KEY] == YOUR_TOKEN_KEY:
            config[OPENAI_API_KEY] = input("Please enter your OpenAI API key: ")

        if config[TASK_PREFIX] == YOUR_TASK_PREFIX:
            config[TASK_PREFIX] = input("Please enter your task prefix: ")

            with open(config_path, 'w') as config_file:
                json.dump(config, config_file, indent=4)
        
        return config
    except Exception as e:
        logging.error("Failed to load configuration.", exc_info=True)
        raise e


def get_git_diff(config):
    """Get git diff for processing."""
    try:
        output = subprocess.check_output(config[GIT_COMMAND], universal_newlines=True)
        logging.info("Git diff successfully obtained.")
        return output
    except subprocess.CalledProcessError:
        logging.exception("Failed to get diff.")
        return None


def count_tokens(text, config):
    """Count the number of tokens in the given text."""
    tokenizer = tiktoken.encoding_for_model(config[MODEL_NAME])
    token_count = len(tokenizer.encode(text))
    logging.info(f"Total diff tokens: {token_count}")
    return token_count


def check_token_count_and_get_confirmation(diff, config):
    """Check the token count and get user confirmation to proceed."""
    data = prepare_request_data(diff, config)
    token_count = count_tokens(json.dumps(data), config)
    
    if token_count > config[MAX_TOKEN_COUNT]:
        logging.error(f"Request contains too many tokens: {token_count}. Please reduce the size of the request.")
        
        # Add prompt for user to decide whether to proceed or not
        questions = [
            {
                'type': 'confirm',
                'name': 'proceed',
                'message': 'The request contains more tokens than recommended. This may result in additional charges. Do you want to proceed?',
                'default': False
            }
        ]
        answers = prompt(questions)
        if not answers.get('proceed'):
            logging.info("User chose not to proceed due to token count exceeding the limit.")
            return False
    
    return True

def get_commit_suggestions(diff, config):
    """Get commit suggestions from OpenAI API."""
    if not check_token_count_and_get_confirmation(diff, config):
        return None

    data = prepare_request_data(diff, config)
    response = send_request_to_openai(data, config)
    suggestions = process_response(response)
    suggestions = add_prefix_to_suggestions(suggestions)
    return suggestions



def prepare_request_data(diff, config):
    """Prepare data for OpenAI API request."""
    git_command = ' '.join(config[GIT_COMMAND])
    message_content = config[MESSAGE_TEMPLATE].format(git_command=git_command, diff=diff)
    return {
        'model': config[MODEL_NAME],
        'messages': [{
            'role': 'user', 
            'content': message_content
        }],
        'temperature': config[TEMPERATURE]
    }


def send_request_to_openai(data, config):
    """Send request to OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config[OPENAI_API_KEY]}',
    }
    try:
        logging.info("Sending request for commit suggestions...")
        response = requests.post(config[OPENAI_API_URL], headers=headers, data=json.dumps(data))
        response.raise_for_status()
        logging.info(f"Response received from API: {response.json()}")
        return response
    except KeyboardInterrupt:
        logging.info("User interrupted execution")
        return None
    except:
        logging.exception("Error when requesting commit suggestions.")
        return None


def process_response(response):
    """Process the response from the OpenAI API."""
    if response is None:
        logging.info("No response to process")
        return []
    try:
        content = response.json()['choices'][0]['message']['content']
        suggestions = normalize_messages(content)
        return suggestions
    except Exception as e:
        logging.error(f"An error occurred during response processing: {str(e)}")
        return []


def normalize_messages(response):
    """Normalize the messages from the OpenAI API response."""
    messages = response.split('\n')[1:]
    messages = [normalize_message_filter(message) for message in messages if len(message) > 1]
    return messages


def normalize_message_filter(message):
    """Normalize a single message."""
    message = message.strip()
    message = re.sub(r"^(\d+\.|-|\*)\s+", "", message)  # remove any initial digits, -, *
    message = re.sub(r"^['\"]", "", message)  # remove any initial quotes
    message = re.sub(r"['\"]$", "", message)  # remove any trailing quotes
    message = re.sub(r"['\"]:", ":", message)  # remove any quotes before colon
    message = re.sub(r":['\"]", ":", message)  # remove any quotes after colon
    message = re.sub(r"\\n", "", message)  # remove any newline characters
    return message.strip()


def add_prefix_to_suggestions(suggestions):
    """Add task ID prefix to suggestions."""
    branch_name = get_current_branch()
    prefix = ""
    if branch_name is not None and branch_name.startswith('feature/IOS-'):
        task_id = branch_name.split('--')[0].split('/')[-1]
        prefix = f'{task_id}: '
        suggestions = [prefix + s.strip() for s in suggestions if s.strip() != '']
    return suggestions

def get_prefix_name():
    """Get prefix name based on current branch."""
    branch_name = get_current_branch()
    prefix = ""
    if branch_name is not None and branch_name.startswith('feature/IOS-'):
        task_id = branch_name.split('--')[0].split('/')[-1]
        prefix = f'{task_id}: '
    return prefix


def get_current_branch():
    """Get current branch name."""
    try:
        branch_name = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], universal_newlines=True).strip()
        return branch_name
    except subprocess.CalledProcessError:
        logging.exception("Failed to get current branch name.")
        return None

def add_prefix_if_needed(commit_message):
    """Add prefix to commit message if needed."""
    branch_name = get_current_branch()
    if branch_name is not None and branch_name.startswith(TASK_PREFIX):
        # Split branch name into parts
        parts = branch_name.split('--')
        # Take the first part (IOS-task-number) and add it to the beginning of the commit message
        if len(parts) > 1:
            task_id = parts[0].split('/')
            commit_message = f'{task_id}: {commit_message}'
    return commit_message


def make_commit(commit_message):
    """Make a commit with the given commit message."""
    try:
        logging.info(f"Making a commit with message: {commit_message}")
        output = subprocess.check_output(["git", "commit", "-m", commit_message], universal_newlines=True)
        logging.info("Commit made successfully.")
        return output
    except subprocess.CalledProcessError:
        logging.exception("Failed to make a commit.")
        return None

def create_custom_commit_message():
    """Create custom commit message with prefix."""
    commit_message = input("Enter your commit message: ")
    commit_message = get_prefix_name() + commit_message
    return commit_message

def prompt_for_commit_message(commit_suggestions):
    """Prompt the user to choose a commit message from the suggestions."""
    commit_suggestions.append('Enter your own commit message')
    questions = [
        {
            'type': 'list',
            'name': 'commit',
            'message': 'Choose your commit message',
            'choices': commit_suggestions
        }
    ]
    commit_message = prompt(questions)['commit']
    if commit_message == 'Enter your own commit message':
        commit_message = create_custom_commit_message()
    return commit_message

def process_diff(diff, config):
    """Process git diff."""
    commit_suggestions = get_commit_suggestions(diff, config)
    if commit_suggestions:
        commit_message = prompt_for_commit_message(commit_suggestions)
        make_commit(commit_message)
    else:
        logging.error("Failed to get commit suggestions.")

  

def main():
    """Main function to control the program flow."""
    args = parse_args()
    configure_logging(args)
    try:
        config = load_config()
        logging.info("Getting git diff...")
        diff = get_git_diff(config)
        if diff:
            process_diff(diff, config)
        else:
            logging.error("Failed to get diff.")
    except KeyboardInterrupt:
        logging.info("Execution interrupted by the user.")
    except Exception as e:
        logging.error("An error occurred during execution.", exc_info=True)
        raise e



if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error("An unhandled error occurred during execution.", exc_info=True)