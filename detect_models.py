#!/usr/bin/env python3
"""
Detect which Claude models are available on your enterprise plan.

This script tests common Claude model IDs by making minimal API calls
and reports which ones work with your API key (Anthropic or Vertex AI).

Usage:
    # For Anthropic API
    python detect_models.py [--update-config]

    # For Vertex AI
    python detect_models.py --vertex --project PROJECT_ID --region REGION [--update-config]

Options:
    --update-config    Automatically update review_config.py with detected models
    --vertex           Use Vertex AI instead of Anthropic API
    --project          Google Cloud project ID (required for Vertex)
    --region           Google Cloud region (default: us-east5)
"""

import argparse
import os
import sys

try:
    from anthropic import Anthropic, AnthropicVertex
except ImportError as e:
    print("Error: anthropic package not installed or missing dependencies", file=sys.stderr)
    print("Install with: pip install 'anthropic[vertex]'", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    sys.exit(1)


# Models to test for Anthropic API, in order of preference
ANTHROPIC_MODELS = [
    # Claude 5 family
    "claude-opus-5",
    "claude-sonnet-5",

    # Claude 4.x family
    "claude-opus-4.8",
    "claude-opus-4-8",
    "claude-opus-4",
    "claude-sonnet-4.6",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-haiku-4-5",

    # Older models (if needed)
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

# Models to test for Vertex AI, in order of preference
VERTEX_MODELS = [
    # Claude 4.x family (newer models)
    "claude-opus-4.8",
    "claude-opus-4-8",
    "claude-sonnet-4.6",
    "claude-sonnet-4-6",

    # Claude 3.5 Sonnet versions
    "claude-3-5-sonnet-v2@20241022",
    "claude-3-5-sonnet@20240620",

    # Claude 3 family
    "claude-3-opus@20240229",
    "claude-3-sonnet@20240229",
    "claude-3-haiku@20240307",

    # Try other naming conventions
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-opus-4",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
]


def test_model(client, model: str) -> tuple[bool, str]:
    """
    Test if a model is available by making a minimal API call.

    Args:
        client: Anthropic or AnthropicVertex client
        model: Model ID to test

    Returns:
        (available: bool, message: str)
    """
    try:
        # Minimal request to test availability (1 token output)
        response = client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return True, "Available"
    except Exception as e:
        error_msg = str(e)

        # Parse common error types
        if "model" in error_msg.lower() and ("not found" in error_msg.lower() or "does not exist" in error_msg.lower()):
            return False, "Model not found"
        elif "permission" in error_msg.lower() or "unauthorized" in error_msg.lower() or "forbidden" in error_msg.lower():
            return False, "No permission"
        elif "invalid" in error_msg.lower():
            return False, "Invalid model ID"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return False, "Rate limited"
        else:
            return False, f"Error: {error_msg[:50]}"


def categorize_models(available_models: list[str]) -> dict:
    """Categorize available models by capability tier."""
    categories = {
        "opus": [],
        "sonnet": [],
        "haiku": [],
        "other": [],
    }

    for model in available_models:
        if "opus" in model:
            categories["opus"].append(model)
        elif "sonnet" in model:
            categories["sonnet"].append(model)
        elif "haiku" in model:
            categories["haiku"].append(model)
        else:
            categories["other"].append(model)

    return categories


def suggest_presets(categories: dict) -> dict:
    """Suggest preset configuration based on available models."""
    # Get best model in each tier
    best_opus = categories["opus"][0] if categories["opus"] else None
    best_sonnet = categories["sonnet"][0] if categories["sonnet"] else None
    best_haiku = categories["haiku"][0] if categories["haiku"] else None

    # Build preset suggestions
    presets = {}

    # Quick preset - prefer Haiku, fallback to Sonnet
    if best_haiku:
        presets["quick"] = {
            "model": best_haiku,
            "max_turns": 25,
            "description": "Fast review for minor changes",
        }
    elif best_sonnet:
        presets["quick"] = {
            "model": best_sonnet,
            "max_turns": 30,
            "description": "Fast review for minor changes",
        }

    # Standard preset - prefer Sonnet
    if best_sonnet:
        presets["standard"] = {
            "model": best_sonnet,
            "max_turns": 50,
            "description": "Standard comprehensive review",
        }

    # Thorough preset - prefer Opus, fallback to best Sonnet
    if best_opus:
        presets["thorough"] = {
            "model": best_opus,
            "max_turns": 75,
            "description": "Deep review for critical changes",
        }
    elif best_sonnet:
        presets["thorough"] = {
            "model": best_sonnet,
            "max_turns": 100,  # More turns to compensate
            "description": "Deep review for critical changes",
        }

    return presets


def generate_config_code(presets: dict) -> str:
    """Generate Python code for review_config.py."""
    lines = ["MODEL_PRESETS = {"]

    for preset_name, config in presets.items():
        lines.append(f'    "{preset_name}": {{')
        lines.append(f'        "model": "{config["model"]}",')
        lines.append(f'        "max_turns": {config["max_turns"]},')
        lines.append(f'        "description": "{config["description"]}",')
        lines.append("    },")

    lines.append("}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Detect available Claude models on your enterprise plan"
    )
    parser.add_argument(
        "--update-config",
        action="store_true",
        help="Automatically update review_config.py with detected models",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed error messages",
    )
    parser.add_argument(
        "--vertex",
        action="store_true",
        help="Use Vertex AI instead of Anthropic API",
    )
    parser.add_argument(
        "--project",
        help="Google Cloud project ID (required for Vertex AI)",
    )
    parser.add_argument(
        "--region",
        default="global",
        help="Google Cloud region (default: global, or use GOOGLE_CLOUD_REGION env var)",
    )
    args = parser.parse_args()

    # Initialize client based on API type
    if args.vertex:
        if not args.project:
            print("Error: --project is required when using --vertex", file=sys.stderr)
            print("\nUsage:", file=sys.stderr)
            print("  python detect_models.py --vertex --project YOUR_PROJECT_ID", file=sys.stderr)
            sys.exit(1)

        print(f"Using Vertex AI (project: {args.project}, region: {args.region})")
        print()

        # Check for required Vertex AI dependencies
        try:
            import google.auth
            import google.cloud.aiplatform
        except ImportError as e:
            print("Error: Missing required dependencies for Vertex AI", file=sys.stderr)
            print("\nInstall with:", file=sys.stderr)
            print("  pip install 'anthropic[vertex]'", file=sys.stderr)
            print("\nThis will install: anthropic, google-auth, google-cloud-aiplatform", file=sys.stderr)
            print(f"\nDetails: {e}", file=sys.stderr)
            sys.exit(1)

        print("Checking Google Cloud authentication...")
        try:
            import google.auth
            credentials, project = google.auth.default()
            print(f"✓ Authenticated (default project: {project or 'none'})")
        except Exception as e:
            print("✗ Not authenticated", file=sys.stderr)
            print("\nAuthenticate with:", file=sys.stderr)
            print("  gcloud auth application-default login", file=sys.stderr)
            print(f"\nDetails: {e}", file=sys.stderr)
            sys.exit(1)

        print()

        try:
            client = AnthropicVertex(project_id=args.project, region=args.region)
        except Exception as e:
            error_msg = str(e)
            print(f"Error initializing Vertex AI client: {error_msg}", file=sys.stderr)

            if "region" in error_msg.lower() or "location" in error_msg.lower():
                print("\nThe region might not support Claude models.", file=sys.stderr)
                print("Common regions for Claude:", file=sys.stderr)
                print("  - us-east5", file=sys.stderr)
                print("  - us-central1", file=sys.stderr)
                print("  - europe-west1", file=sys.stderr)
                print("\nTry: --region us-east5", file=sys.stderr)
            else:
                print("\nMake sure:", file=sys.stderr)
                print("  1. You're authenticated: gcloud auth application-default login", file=sys.stderr)
                print("  2. Vertex AI API is enabled: gcloud services enable aiplatform.googleapis.com", file=sys.stderr)
                print("  3. You have permissions: roles/aiplatform.user", file=sys.stderr)
            sys.exit(1)

        models_to_test = VERTEX_MODELS
        api_type = "Vertex AI"
    else:
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
            print("\nSet your API key first:", file=sys.stderr)
            print("  export ANTHROPIC_API_KEY=your-api-key", file=sys.stderr)
            print("\nOr use Vertex AI:", file=sys.stderr)
            print("  python detect_models.py --vertex --project YOUR_PROJECT_ID", file=sys.stderr)
            sys.exit(1)

        print("Using Anthropic API")
        print()
        client = Anthropic(api_key=api_key)
        models_to_test = ANTHROPIC_MODELS
        api_type = "Anthropic API"

    print(f"Detecting available Claude models on {api_type}...")
    print(f"Testing {len(models_to_test)} model IDs...")
    print("-" * 60)

    available = []
    unavailable = []

    for model in models_to_test:
        print(f"Testing {model:35s} ... ", end="", flush=True)
        is_available, message = test_model(client, model)

        if is_available:
            print(f"✓ {message}")
            available.append(model)
        else:
            print(f"✗ {message}")
            unavailable.append((model, message))
            if args.verbose and "Error:" in message:
                print(f"  Details: {message}")

    print("-" * 60)
    print(f"\nResults: {len(available)} available, {len(unavailable)} unavailable\n")

    if not available:
        print("⚠️  No models detected!")
        print("\nPossible issues:")
        print("  - Invalid API key")
        print("  - Network connectivity problems")
        print("  - All tested models unavailable on your plan")
        print("\nTry running with --verbose for more details")
        sys.exit(1)

    # Categorize and display
    categories = categorize_models(available)

    print("Available models by tier:")
    print()

    if categories["opus"]:
        print("  Opus (highest capability):")
        for model in categories["opus"]:
            print(f"    - {model}")
        print()

    if categories["sonnet"]:
        print("  Sonnet (balanced):")
        for model in categories["sonnet"]:
            print(f"    - {model}")
        print()

    if categories["haiku"]:
        print("  Haiku (fastest):")
        for model in categories["haiku"]:
            print(f"    - {model}")
        print()

    if categories["other"]:
        print("  Other:")
        for model in categories["other"]:
            print(f"    - {model}")
        print()

    # Generate preset suggestions
    presets = suggest_presets(categories)

    if not presets:
        print("⚠️  Could not generate preset suggestions (no suitable models found)")
        sys.exit(1)

    print("Suggested preset configuration:")
    print("-" * 60)
    config_code = generate_config_code(presets)
    print(config_code)
    print("-" * 60)

    # Update config if requested
    if args.update_config:
        print("\nUpdating review_config.py...")

        try:
            # Read existing config
            with open("review_config.py", "r") as f:
                content = f.read()

            # Find MODEL_PRESETS section
            import re
            pattern = r"MODEL_PRESETS:\s*Dict\[str,\s*Dict\[str,\s*Any\]\]\s*=\s*\{[^}]+\}"

            if re.search(pattern, content, re.DOTALL):
                # Replace existing MODEL_PRESETS
                new_section = f"MODEL_PRESETS: Dict[str, Dict[str, Any]] = {{\n"
                for preset_name, config in presets.items():
                    new_section += f'    "{preset_name}": {{\n'
                    new_section += f'        "model": "{config["model"]}",\n'
                    new_section += f'        "max_turns": {config["max_turns"]},\n'
                    new_section += f'        "description": "{config["description"]}",\n'
                    new_section += "    },\n"
                new_section += "}"

                new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

                # Backup and write
                with open("review_config.py.backup", "w") as f:
                    f.write(content)

                with open("review_config.py", "w") as f:
                    f.write(new_content)

                print("✓ Updated review_config.py")
                print("  Backup saved to review_config.py.backup")
            else:
                print("⚠️  Could not find MODEL_PRESETS in review_config.py")
                print("  Please update manually using the configuration above")

        except Exception as e:
            print(f"✗ Error updating config: {e}")
            print("  Please update review_config.py manually")
    else:
        print("\nTo use this configuration:")
        print("  1. Copy the configuration above")
        print("  2. Edit review_config.py")
        print("  3. Replace MODEL_PRESETS = { ... } with the suggested config")
        print("\nOr run with --update-config to update automatically")

    print("\nDetection complete!")


if __name__ == "__main__":
    main()
