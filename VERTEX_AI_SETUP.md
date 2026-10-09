# Vertex AI Setup Guide

This guide shows how to use the OpenStack review skill with Google Cloud's Vertex AI for Claude models.

## Prerequisites

1. Google Cloud project with Vertex AI API enabled
2. Google Cloud CLI (`gcloud`) installed
3. Appropriate IAM permissions for Vertex AI

## Setup Steps

### 1. Install Dependencies

**Option A: Install with Vertex AI support (recommended):**
```bash
pip install claude-agent-sdk 'anthropic[vertex]'
```

This installs:
- `claude-agent-sdk` - Agent SDK
- `anthropic` - Anthropic API client
- `google-auth` - Google Cloud authentication
- `google-cloud-aiplatform` - Vertex AI platform

**Option B: Install from requirements file:**
```bash
# Edit requirements.txt and uncomment the anthropic[vertex] line
pip install -r requirements.txt
```

**Option C: Install separately:**
```bash
pip install claude-agent-sdk anthropic google-auth google-cloud-aiplatform
```

### 2. Authenticate with Google Cloud

```bash
# Login with your Google account
gcloud auth application-default login

# Set your project (optional, can also use --vertex-project flag)
gcloud config set project YOUR_PROJECT_ID
```

### 3. Enable Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com
```

### 4. Detect Available Models

Run the detection script to find which Claude models are available in your Vertex AI project:

```bash
python detect_models.py --vertex --project YOUR_PROJECT_ID
```

**Example output:**
```
Using Vertex AI (project: my-project, region: global)
Make sure you're authenticated with: gcloud auth application-default login

Detecting available Claude models on Vertex AI...
Testing 11 model IDs...
------------------------------------------------------------
Testing claude-3-5-sonnet-v2@20241022      ... ✓ Available
Testing claude-3-5-sonnet@20240620         ... ✓ Available
Testing claude-3-opus@20240229             ... ✓ Available
Testing claude-3-sonnet@20240229           ... ✓ Available
Testing claude-3-haiku@20240307            ... ✓ Available

Available models by tier:
  Opus (highest capability):
    - claude-3-opus@20240229
  
  Sonnet (balanced):
    - claude-3-5-sonnet-v2@20241022
    - claude-3-5-sonnet@20240620
    - claude-3-sonnet@20240229
  
  Haiku (fastest):
    - claude-3-haiku@20240307

Suggested preset configuration:
------------------------------------------------------------
MODEL_PRESETS = {
    "quick": {
        "model": "claude-3-haiku@20240307",
        "max_turns": 25,
        "description": "Fast review for minor changes",
    },
    "standard": {
        "model": "claude-3-5-sonnet-v2@20241022",
        "max_turns": 50,
        "description": "Standard comprehensive review",
    },
    "thorough": {
        "model": "claude-3-opus@20240229",
        "max_turns": 75,
        "description": "Deep review for critical changes",
    },
}
```

### 5. Update Configuration

Option A: **Automatic** (recommended)
```bash
python detect_models.py --vertex --project YOUR_PROJECT_ID --update-config
```

Option B: **Manual**
1. Copy the suggested `MODEL_PRESETS` from the detection output
2. Edit `review_config.py`
3. Replace the `MODEL_PRESETS` dictionary

## Running Reviews with Vertex AI

### Method 1: Environment Variables (Recommended)

Set environment variables once:

```bash
export CLAUDE_CODE_USE_VERTEX=1
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
export CLOUD_ML_REGION=global  # Optional, defaults to global
```

Then run reviews normally:

```bash
python review_agent.py 970404
python review_agent.py 970404 --preset thorough
```

### Method 2: Using gcloud Default Project

If you've set a default project with `gcloud config set project`:

```bash
# Set default project
gcloud config set project your-project-id

# Set env var to use default project
export ANTHROPIC_VERTEX_PROJECT_ID=$(gcloud config get-value project)

# Run review
python review_agent.py 970404
```

## Vertex AI Model Names

Vertex AI uses different model IDs than the Anthropic API:

| Vertex AI Model ID | Equivalent Anthropic API | Description |
|-------------------|-------------------------|-------------|
| `claude-opus-4.8` | `claude-opus-4.8` | Claude Opus 4.8 (latest) |
| `claude-sonnet-4.6` | `claude-sonnet-4.6` | Claude Sonnet 4.6 (latest) |
| `claude-3-5-sonnet-v2@20241022` | `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet v2 |
| `claude-3-5-sonnet@20240620` | `claude-3-5-sonnet-20240620` | Claude 3.5 Sonnet |
| `claude-3-opus@20240229` | `claude-3-opus-20240229` | Claude 3 Opus |
| `claude-3-sonnet@20240229` | `claude-3-sonnet-20240229` | Claude 3 Sonnet |
| `claude-3-haiku@20240307` | `claude-3-haiku-20240307` | Claude 3 Haiku |

**Note:** Model availability and naming conventions may vary by organization and region. Run the detection script to see which models are available in your setup.

## Available Regions

Common Vertex AI regions for Claude models:

- `global` (default, uses Google's global endpoint)
- `global`
- `us-central1`
- `europe-west1`
- `asia-southeast1`

**Note:** The available regions depend on your organization's Vertex AI configuration. Use the region specified by your organization's policy.

Check [Vertex AI locations](https://cloud.google.com/vertex-ai/docs/general/locations) for the full list.

## Complete Example Workflow

```bash
# 1. Authenticate
gcloud auth application-default login

# 2. Set project (optional)
export ANTHROPIC_VERTEX_PROJECT_ID=my-openstack-project
export CLOUD_ML_REGION=global

# 3. Detect and configure models
python detect_models.py --vertex --project $ANTHROPIC_VERTEX_PROJECT_ID --update-config

# 4. Run a review
python review_agent.py 970404

# 5. Run with specific preset
python review_agent.py 970405 --preset thorough

# 6. Override model
python review_agent.py 970406 --model claude-3-opus@20240229
```

## Troubleshooting

### "Please run: gcloud auth application-default login"

You're not authenticated. Run:
```bash
gcloud auth application-default login
```

### "Permission denied" or "403 Forbidden"

Your account doesn't have Vertex AI permissions. Required IAM roles:
- `roles/aiplatform.user` (to use Vertex AI)

Ask your Google Cloud admin to grant these, or:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/aiplatform.user"
```

### "Project not found" or "404"

- Verify project ID: `gcloud projects list`
- Enable Vertex AI API: `gcloud services enable aiplatform.googleapis.com`

### "Model not found"

The model isn't available in your region. Try:
1. Different region: `export CLOUD_ML_REGION=us-central1`
2. Run detection to see available models: `python detect_models.py --vertex --project YOUR_PROJECT`

### Rate Limiting

Vertex AI has quota limits. If you hit them:
- Wait and retry
- Request quota increase in Google Cloud Console
- Use a lower-tier model preset (`--preset quick`)

## Cost Considerations

Vertex AI charges for:
1. **Input tokens**: Text sent to the model
2. **Output tokens**: Text generated by the model

Approximate token usage per review:
- **Quick review** (~5-10k tokens): $0.05 - $0.20
- **Standard review** (~20-30k tokens): $0.20 - $0.60
- **Thorough review** (~50-100k tokens): $0.50 - $2.00

Actual costs depend on:
- Model used (Opus > Sonnet > Haiku)
- Change complexity
- Number of files
- Amount of context

Check your costs:
```bash
gcloud alpha billing accounts describe YOUR_BILLING_ACCOUNT_ID
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_CODE_USE_VERTEX` | Enable Vertex AI mode | `1` |
| `ANTHROPIC_VERTEX_PROJECT_ID` | Your Google Cloud project ID | `my-openstack-project` |
| `CLOUD_ML_REGION` | Vertex AI region | `global` |
| `REVIEW_PRESET` | Default review preset | `thorough` |
| `REVIEW_MODEL` | Override model | `claude-3-opus@20240229` |

## Comparing with Anthropic API

| Feature | Anthropic API | Vertex AI |
|---------|--------------|-----------|
| Authentication | API key | Google Cloud auth |
| Model names | `claude-opus-5` | `claude-3-opus@20240229` |
| Billing | Anthropic account | Google Cloud billing |
| Rate limits | Per API key | Per GCP project |
| Enterprise controls | Limited | Full GCP IAM |
| Data residency | Anthropic controlled | Choose GCP region |

## Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Claude on Vertex AI](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/claude)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)
- [Google Cloud Regions](https://cloud.google.com/vertex-ai/docs/general/locations)

## Next Steps

After setup:
1. Review the [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) for preset customization
2. See [QUICKSTART.md](QUICKSTART.md) for usage examples
3. Check [README.md](README.md) for full feature list
