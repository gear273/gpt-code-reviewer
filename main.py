import os
import openai
import requests
import yaml

from rich.console import Console
from rich.markdown import Markdown


from prompts import get_code_prompt, get_system_prompt


config = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")
user = config["user"]
repositories = config["repositories"]
MODEL_ENGINE = config["model_engine"]
MAX_LENGTH = 4096

console = Console()


def print_options(repository, pull_request):
    console.print(
        Markdown(
            f"""You have chosen to review {repository} pull request {pull_request} 
                enter `r` to review the code, `q` to quit, `h` for help and `n` 
                to review a different pull request."""
        )
    )


def send_system_message(messages):
    response = openai.ChatCompletion.create(model=MODEL_ENGINE, messages=messages)
    return response


def fetch_data(repository, pull_request, accept="application/vnd.github.v3.diff"):
    url = f"https://api.github.com/repos/{user}/{repository}/pulls/{pull_request}"
    headers = {"Accept": accept, "Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    return response


def get_repo_and_pr():
    while True:
        console.print("Select a repository:")
        for index, repo in enumerate(repositories):
            console.print(f"{index + 1}. {repo}")

        try:
            selection = int(input("Enter the number of the repository: "))
            if 1 <= selection <= len(repositories):
                repository = repositories[selection - 1]
                break
        except ValueError:
            pass

        console.print(
            f"Invalid input. Please enter a number between 1 and {len(repositories)}"
        )

    pull_request = input("Enter the number of the pull request: ").strip()

    return repository, pull_request


def review():
    repository, pull_request = get_repo_and_pr()

    print_options(repository, pull_request)

    if not pull_request:
        get_repo_and_pr()

    messages = [{"role": "system", "content": get_system_prompt()}]

    console.print("Loading Skynet...")
    send_system_message(messages)
    console.print("Skynet loaded!")

    data = fetch_data(repository, pull_request, "application/vnd.github.v3+json")
    messages.append({"role": "user", "content": data.json()["body"]})
    messages.append({"role": "user", "content": data.json()["title"]})

    while True:
        user_input = input("👨: ")

        if user_input == "q":
            break

        if user_input == "h":
            console.print(
                Markdown(
                    "Enter `r` to review the code, `q` to quit and `n` to review a different pull request."
                )
            )
            continue

        if user_input == "n":
            messages = [{"role": "system", "content": get_system_prompt()}]
            repository, pull_request = get_repo_and_pr()
            data = fetch_data(
                repository, pull_request, "application/vnd.github.v3+json"
            )
            messages.append({"role": "user", "content": data.json()["body"]})
            messages.append({"role": "user", "content": data.json()["title"]})
            print_options(repository, pull_request)
            continue

        if user_input == "r":
            response = fetch_data(repository, pull_request)

            code = response.text[: MAX_LENGTH - len(get_code_prompt(""))]

            prompt = get_code_prompt(code)

            messages.append({"role": "user", "content": prompt})

        if user_input:
            console.print("Thinking...")
            messages.append({"role": "user", "content": user_input})

        completion = openai.ChatCompletion.create(
            model=MODEL_ENGINE,
            messages=messages,
        )

        reply = completion["choices"][0]["message"]["content"]
        console.print(Markdown("🤖: "))
        console.print(Markdown(reply))
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    review()
